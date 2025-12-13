import asyncio
import json
import websockets
import os
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from ..database.session import SessionLocal
from ..database.models import CallLog, ActiveCall
from .call_manager import call_manager

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_REALTIME_URL = (
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
)

SYSTEM_PROMPT = """You are Cortana, an AI voice assistant for home-services businesses. You are friendly, professional, and efficient. Your goals are to:
1. Answer customer questions about services and pricing
2. Book appointments when requested
3. Handle emergencies by escalating to available technicians
4. Provide helpful information about business hours and service areas

Keep responses concise and conversational - remember this is a phone call, not a text chat. Be warm but efficient."""


async def handle_realtime_voice(websocket: WebSocket):
    await websocket.accept()
    
    stream_sid = None
    call_sid = None
    openai_ws = None
    transcripts = []
    business_id = 1
    caller_number = "Unknown"
    
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            await websocket.close(code=1011, reason="Service unavailable")
            return
            
        openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            },
        )

        print("OpenAI Realtime connected")
        
        session_update = {
            "type": "session.update",
            "session": {
                "voice": "alloy",
                "instructions": SYSTEM_PROMPT,
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }
        await openai_ws.send(json.dumps(session_update))
        print("Session configured for g711_ulaw audio")

        async def receive_from_twilio():
            nonlocal stream_sid, call_sid, caller_number
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    if data["event"] == "start":
                        stream_sid = data["start"]["streamSid"]
                        call_sid = data["start"].get("callSid", stream_sid)
                        
                        custom_params = data["start"].get("customParameters", {})
                        caller_number = custom_params.get("from", "Unknown")
                        
                        print(f"Twilio stream started: {stream_sid}, Call SID: {call_sid}")
                        
                        call_manager.start_call(call_sid, business_id, caller_number)
                        
                    elif data["event"] == "media":
                        audio_payload = data["media"]["payload"]
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": audio_payload
                        }
                        await openai_ws.send(json.dumps(audio_append))
                        
                    elif data["event"] == "stop":
                        print("Twilio stream stopped")
                        break
                        
            except WebSocketDisconnect:
                print("Twilio WebSocket disconnected")
            except Exception as e:
                print(f"Twilio receive error: {e}")

        async def receive_from_openai():
            nonlocal stream_sid, transcripts, call_sid
            try:
                async for message in openai_ws:
                    response = json.loads(message)
                    
                    if response["type"] == "response.audio.delta":
                        if stream_sid:
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": response["delta"]
                                }
                            }
                            await websocket.send_text(json.dumps(audio_delta))
                            
                    elif response["type"] == "input_audio_buffer.speech_started":
                        print("User started speaking")
                        if stream_sid:
                            clear_event = {
                                "event": "clear",
                                "streamSid": stream_sid
                            }
                            await websocket.send_text(json.dumps(clear_event))
                            
                    elif response["type"] == "conversation.item.input_audio_transcription.completed":
                        transcript = response.get("transcript", "")
                        if transcript:
                            print(f"User said: {transcript}")
                            transcripts.append({"speaker": "customer", "text": transcript})
                            if call_sid:
                                call_manager.add_transcript(call_sid, "customer", transcript)
                        
                    elif response["type"] == "response.audio_transcript.done":
                        transcript = response.get("transcript", "")
                        if transcript:
                            print(f"Cortana said: {transcript}")
                            transcripts.append({"speaker": "cortana", "text": transcript})
                            if call_sid:
                                call_manager.add_transcript(call_sid, "cortana", transcript)
                        
                    elif response["type"] == "error":
                        print(f"OpenAI error: {response}")
                        
            except Exception as e:
                print(f"OpenAI receive error: {e}")

        await asyncio.gather(
            receive_from_twilio(),
            receive_from_openai()
        )
        
    except websockets.exceptions.WebSocketException as e:
        print(f"OpenAI WebSocket connection failed: {e}")
        try:
            await websocket.close(code=1011, reason="AI service unavailable")
        except:
            pass
    except Exception as e:
        print(f"Realtime connection error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
    finally:
        if openai_ws:
            try:
                await openai_ws.close()
            except:
                pass
        
        if call_sid and transcripts:
            try:
                db = SessionLocal()
                transcript_text = "\n".join([
                    f"{t['speaker']}: {t['text']}" for t in transcripts
                ])
                
                call_log = CallLog(
                    business_id=business_id,
                    call_sid=call_sid,
                    caller_number=caller_number,
                    transcript=transcript_text,
                    sentiment="neutral",
                    disposition="completed",
                    language="en"
                )
                db.add(call_log)
                db.commit()
                db.close()
                print(f"Call log saved: {call_sid}")
            except Exception as e:
                print(f"Error saving call log: {e}")
        
        if call_sid:
            call_manager.end_call(call_sid)
        
        print("Realtime session ended")
