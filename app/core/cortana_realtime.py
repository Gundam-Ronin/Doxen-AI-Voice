import asyncio
import json
import websockets
import os
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from ..database.session import SessionLocal
from ..database.models import CallLog, ActiveCall, Technician
from .call_manager import call_manager
from .data_extractor import CustomerDataCollector, extract_customer_data_ai
from .intent_detector import detect_intent, CustomerIntent, is_booking_intent, is_urgent, get_intent_response_hint
from .calendar import calendar_service
from .dispatcher import dispatcher

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_REALTIME_URL = (
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
)

SYSTEM_PROMPT = """You are Cortana, an AI voice assistant for home-services businesses. You are friendly, professional, and efficient. Your goals are to:
1. Answer customer questions about services and pricing
2. Book appointments when requested - ask for their name, phone number, and address
3. Handle emergencies by escalating to available technicians
4. Provide helpful information about business hours and service areas

IMPORTANT BEHAVIORS:
- Keep responses concise and conversational - this is a phone call
- When a customer wants to book an appointment:
  1. Ask for their name if they haven't provided it
  2. Ask for their phone number for confirmation
  3. Ask for their service address
  4. Offer available time slots
  5. Confirm the booking details
- For emergencies, reassure the customer and let them know a technician will be dispatched immediately
- Always confirm important details by repeating them back
- Be warm but efficient - respect the caller's time"""


class RealtimeCallHandler:
    """Handles a single realtime voice call with full Phase 7 capabilities."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid = None
        self.call_sid = None
        self.openai_ws = None
        self.transcripts = []
        self.business_id = 1
        self.caller_number = "Unknown"
        self.data_collector = CustomerDataCollector()
        self.booking_in_progress = False
        self.pending_slot = None
        self.confirmed_booking = None
    
    async def handle(self):
        """Main entry point for handling the realtime call."""
        await self.websocket.accept()
        
        try:
            if not OPENAI_API_KEY:
                print("OpenAI API key not configured")
                await self.websocket.close(code=1011, reason="Service unavailable")
                return
            
            self.openai_ws = await websockets.connect(
                OPENAI_REALTIME_URL,
                additional_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                },
            )
            
            if not self.openai_ws:
                print("Failed to connect to OpenAI Realtime")
                await self.websocket.close(code=1011, reason="AI connection failed")
                return
            
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
            await self.openai_ws.send(json.dumps(session_update))
            print("Session configured for g711_ulaw audio")
            
            await asyncio.gather(
                self.receive_from_twilio(),
                self.receive_from_openai()
            )
            
        except websockets.exceptions.WebSocketException as e:
            print(f"OpenAI WebSocket connection failed: {e}")
            try:
                await self.websocket.close(code=1011, reason="AI service unavailable")
            except:
                pass
        except Exception as e:
            print(f"Realtime connection error: {e}")
            try:
                await self.websocket.close(code=1011, reason="Internal error")
            except:
                pass
        finally:
            await self.cleanup()
    
    async def receive_from_twilio(self):
        """Handle incoming messages from Twilio."""
        try:
            while True:
                message = await self.websocket.receive_text()
                data = json.loads(message)
                
                if data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    self.call_sid = data["start"].get("callSid", self.stream_sid)
                    
                    custom_params = data["start"].get("customParameters", {})
                    self.caller_number = custom_params.get("from", "Unknown")
                    
                    print(f"Twilio stream started: {self.stream_sid}, Call SID: {self.call_sid}")
                    
                    call_manager.start_call(self.call_sid, self.business_id, self.caller_number)
                    self.data_collector.data["phone"] = self.caller_number if self.caller_number != "Unknown" else None
                    
                elif data["event"] == "media":
                    audio_payload = data["media"]["payload"]
                    audio_append = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_payload
                    }
                    if self.openai_ws:
                        await self.openai_ws.send(json.dumps(audio_append))
                    
                elif data["event"] == "stop":
                    print("Twilio stream stopped")
                    break
                    
        except WebSocketDisconnect:
            print("Twilio WebSocket disconnected")
        except Exception as e:
            print(f"Twilio receive error: {e}")
    
    async def receive_from_openai(self):
        """Handle incoming messages from OpenAI."""
        if not self.openai_ws:
            return
        try:
            async for message in self.openai_ws:
                response = json.loads(message)
                
                if response["type"] == "response.audio.delta":
                    if self.stream_sid:
                        audio_delta = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {
                                "payload": response["delta"]
                            }
                        }
                        await self.websocket.send_text(json.dumps(audio_delta))
                        
                elif response["type"] == "input_audio_buffer.speech_started":
                    print("User started speaking")
                    if self.stream_sid:
                        clear_event = {
                            "event": "clear",
                            "streamSid": self.stream_sid
                        }
                        await self.websocket.send_text(json.dumps(clear_event))
                        
                elif response["type"] == "conversation.item.input_audio_transcription.completed":
                    transcript = response.get("transcript", "")
                    if transcript:
                        await self.handle_customer_speech(transcript)
                    
                elif response["type"] == "response.audio_transcript.done":
                    transcript = response.get("transcript", "")
                    if transcript:
                        await self.handle_cortana_speech(transcript)
                    
                elif response["type"] == "error":
                    print(f"OpenAI error: {response}")
                    
        except Exception as e:
            print(f"OpenAI receive error: {e}")
    
    async def handle_customer_speech(self, transcript: str):
        """Process customer speech for intent and data extraction."""
        print(f"User said: {transcript}")
        self.transcripts.append({"speaker": "customer", "text": transcript})
        
        if self.call_sid:
            call_manager.add_transcript(self.call_sid, "customer", transcript)
        
        self.data_collector.add_utterance("customer", transcript)
        
        intent, confidence = detect_intent(transcript)
        print(f"Detected intent: {intent.value} (confidence: {confidence:.2f})")
        
        if is_urgent(intent):
            await self.handle_emergency()
        elif is_booking_intent(intent) and not self.booking_in_progress:
            self.booking_in_progress = True
            await self.start_booking_flow()
        elif intent == CustomerIntent.CONFIRMATION and self.pending_slot:
            await self.confirm_booking()
    
    async def handle_cortana_speech(self, transcript: str):
        """Track Cortana's responses."""
        print(f"Cortana said: {transcript}")
        self.transcripts.append({"speaker": "cortana", "text": transcript})
        
        if self.call_sid:
            call_manager.add_transcript(self.call_sid, "cortana", transcript)
    
    async def start_booking_flow(self):
        """Initialize the booking flow by getting available slots."""
        try:
            slots = await calendar_service.get_availability(days_ahead=7)
            if slots:
                self.pending_slot = slots[0]
                print(f"Available slot: {self.pending_slot['display']}")
        except Exception as e:
            print(f"Error getting availability: {e}")
    
    async def confirm_booking(self):
        """Confirm and create the booking."""
        if not self.pending_slot:
            return
        
        try:
            customer_data = await self.data_collector.finalize_extraction()
            
            result = await calendar_service.book_appointment(
                summary=f"Service Appointment - {customer_data.get('name', 'Customer')}",
                description=customer_data.get('service_needed', 'General service'),
                start_time=self.pending_slot['start'],
                customer_info=customer_data
            )
            
            if result and result.get('success'):
                self.confirmed_booking = result
                print(f"Booking confirmed: {result}")
                
                await self.send_confirmations(customer_data)
                await self.dispatch_technician(customer_data)
            
            self.pending_slot = None
            
        except Exception as e:
            print(f"Booking error: {e}")
    
    async def send_confirmations(self, customer_data: dict):
        """Send SMS confirmation to customer."""
        phone = customer_data.get('phone') or self.caller_number
        if phone and phone != "Unknown":
            try:
                dispatcher.send_customer_confirmation(
                    customer_phone=phone,
                    business_name="Our Service Company",
                    appointment_time=self.pending_slot['display'] if self.pending_slot else "As scheduled"
                )
                print(f"Confirmation SMS sent to {phone}")
            except Exception as e:
                print(f"SMS confirmation error: {e}")
    
    async def dispatch_technician(self, customer_data: dict):
        """Match and dispatch an available technician."""
        try:
            db = SessionLocal()
            technicians = db.query(Technician).filter(
                Technician.business_id == self.business_id,
                Technician.is_available == True
            ).all()
            db.close()
            
            if technicians:
                tech = technicians[0]
                dispatcher.dispatch_technician(
                    technician_name=tech.name,
                    technician_phone=tech.phone,
                    customer_info={
                        "name": customer_data.get('name', 'Customer'),
                        "phone": customer_data.get('phone') or self.caller_number,
                        "address": customer_data.get('address', 'To be confirmed')
                    },
                    appointment_time=self.pending_slot['display'] if self.pending_slot else "ASAP",
                    service_type=customer_data.get('service_needed', 'General service')
                )
                print(f"Technician {tech.name} dispatched")
        except Exception as e:
            print(f"Dispatch error: {e}")
    
    async def handle_emergency(self):
        """Handle emergency dispatch."""
        try:
            customer_data = self.data_collector.get_data()
            
            db = SessionLocal()
            technicians = db.query(Technician).filter(
                Technician.business_id == self.business_id,
                Technician.is_available == True
            ).all()
            db.close()
            
            if technicians:
                tech_list = [{"name": t.name, "phone": t.phone, "is_available": t.is_available} for t in technicians]
                dispatcher.notify_emergency(tech_list, {
                    "customer_phone": customer_data.get('phone') or self.caller_number,
                    "issue": customer_data.get('service_needed', 'Emergency service needed'),
                    "address": customer_data.get('address', 'To be confirmed')
                })
                print("Emergency dispatched to technicians")
        except Exception as e:
            print(f"Emergency dispatch error: {e}")
    
    async def cleanup(self):
        """Clean up resources and save call log."""
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except:
                pass
        
        if self.call_sid and self.transcripts:
            try:
                customer_data = await self.data_collector.finalize_extraction()
                
                db = SessionLocal()
                transcript_text = "\n".join([
                    f"{t['speaker']}: {t['text']}" for t in self.transcripts
                ])
                
                call_log = CallLog(
                    business_id=self.business_id,
                    call_sid=self.call_sid,
                    caller_number=self.caller_number,
                    transcript=transcript_text,
                    sentiment="neutral",
                    disposition="completed",
                    language="en",
                    customer_name=customer_data.get('name'),
                    customer_phone=customer_data.get('phone'),
                    customer_email=customer_data.get('email'),
                    customer_address=customer_data.get('address'),
                    booked_appointment=self.confirmed_booking is not None,
                    is_emergency=False
                )
                db.add(call_log)
                db.commit()
                db.close()
                print(f"Call log saved: {self.call_sid}")
            except Exception as e:
                print(f"Error saving call log: {e}")
        
        if self.call_sid:
            call_manager.end_call(self.call_sid)
        
        print("Realtime session ended")


async def handle_realtime_voice(websocket: WebSocket):
    """Entry point for realtime voice handling."""
    handler = RealtimeCallHandler(websocket)
    await handler.handle()
