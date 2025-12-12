import asyncio
import json
import websockets
import base64
import os
from fastapi import WebSocket, WebSocketDisconnect

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
    
    try:
        async with websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            },
        ) as openai_ws:

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
            print("Session configured")

            async def receive_from_twilio():
                nonlocal stream_sid
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        
                        if data["event"] == "start":
                            stream_sid = data["start"]["streamSid"]
                            print(f"Twilio stream started: {stream_sid}")
                            
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

            async def receive_from_openai():
                nonlocal stream_sid
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
                            print(f"User said: {transcript}")
                            
                        elif response["type"] == "response.audio_transcript.done":
                            transcript = response.get("transcript", "")
                            print(f"Cortana said: {transcript}")
                            
                        elif response["type"] == "error":
                            print(f"OpenAI error: {response}")
                            
                except Exception as e:
                    print(f"OpenAI receive error: {e}")

            await asyncio.gather(
                receive_from_twilio(),
                receive_from_openai()
            )
            
    except Exception as e:
        print(f"Realtime connection error: {e}")
    finally:
        print("Realtime session ended")
