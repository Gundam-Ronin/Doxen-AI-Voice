"""
Cortana Realtime Voice Handler - Phase 6 Universal Platform
Handles real-time voice calls with OpenAI Realtime API.
Now with multi-tenant support and universal engines.
"""

import asyncio
import json
import websockets
import os
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from ..database.session import SessionLocal
from ..database.models import Business, CallLog, Call, ActiveCall, Technician, Customer
from .call_manager import call_manager
from .universal_intent_engine import universal_intent_engine, UniversalIntent
from .universal_field_extractor import universal_field_extractor, ExtractionSchema
from .universal_dispatch_engine import universal_dispatch_engine
from .universal_appointment_engine import universal_appointment_engine
from .dispatcher import dispatcher
from .email_service import email_service
from .outbound_calling import outbound_calling_engine, OutboundCallRequest, OutboundCallType
from .quote_generator import quote_generator

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_REALTIME_URL = (
    "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
)


def generate_system_prompt(business: dict) -> str:
    """Generate a dynamic system prompt based on business profile."""
    business_name = business.get("name", "our company")
    industry = business.get("industry", "home services")
    personality = business.get("ai_personality", "friendly and professional")
    
    services = []
    if business.get("service_categories"):
        services = [cat.get("name", "") for cat in business.get("service_categories", [])]
    elif business.get("services"):
        services = business.get("services", [])
    
    services_str = ", ".join(services[:5]) if services else "our services"
    
    custom_fields = business.get("custom_fields", [])
    additional_questions = ""
    if custom_fields:
        field_names = [f.get("field_name", "") for f in custom_fields[:3]]
        additional_questions = f"\n- If relevant, ask about: {', '.join(field_names)}"
    
    return f"""You are Cortana, the AI voice assistant for {business_name}, a {industry} company. You are {personality}. Your goals are to:
1. Answer customer questions about services and pricing
2. Book appointments when requested - collect name, phone, address, and service details
3. Handle emergencies by escalating to available technicians immediately
4. Provide helpful information about business hours and service areas

AVAILABLE SERVICES: {services_str}

IMPORTANT BEHAVIORS:
- Keep responses concise and conversational - this is a phone call
- When a customer wants to book an appointment:
  1. Ask for their name if they haven't provided it
  2. Ask for their phone number for confirmation
  3. Ask for their service address
  4. Ask what service they need{additional_questions}
  5. Offer available time slots
  6. Confirm the booking details
- For emergencies, reassure the customer and let them know a technician will be dispatched immediately
- Always confirm important details by repeating them back
- Be warm but efficient - respect the caller's time
- If you don't know specific pricing, offer to have someone call them back with a quote"""


class RealtimeCallHandler:
    """Handles a single realtime voice call with Phase 6 Universal Platform capabilities."""
    
    def __init__(self, websocket: WebSocket, business_id: int = None):
        self.websocket = websocket
        self.stream_sid = None
        self.call_sid = None
        self.openai_ws = None
        self.transcripts = []
        self.business_id = business_id or 1
        self.business = None
        self.caller_number = "Unknown"
        self.booking_in_progress = False
        self.pending_slot = None
        self.confirmed_booking = None
        self.customer_id = None
        self.detected_intents = []
        self.extraction_schema = None
    
    def _load_business(self):
        """Load business profile from database."""
        try:
            db = SessionLocal()
            business = db.query(Business).filter(Business.id == self.business_id).first()
            if business:
                self.business = {
                    "id": business.id,
                    "name": business.name,
                    "industry": business.industry or "general",
                    "ai_personality": business.ai_personality,
                    "coverage_area": business.coverage_area or [],
                    "business_hours": business.business_hours or business.hours or {},
                    "dispatch_rules": business.dispatch_rules or {"mode": "skill_based"},
                    "custom_fields": business.custom_fields or [],
                    "calendar_integration": business.calendar_integration or {},
                    "services": business.services or [],
                    "service_categories": []
                }
                
                if hasattr(business, 'service_categories') and business.service_categories:
                    self.business["service_categories"] = [{
                        "name": cat.name,
                        "sub_services": cat.sub_services or [],
                        "required_fields": cat.required_fields or [],
                        "default_duration_minutes": cat.default_duration_minutes or 60
                    } for cat in business.service_categories]
                
                self.extraction_schema = ExtractionSchema.from_business_profile(self.business)
            db.close()
        except Exception as e:
            print(f"Error loading business: {e}")
            self.business = {
                "id": self.business_id,
                "name": "Our Company",
                "industry": "general",
                "ai_personality": "friendly and professional",
                "dispatch_rules": {"mode": "skill_based"},
                "custom_fields": [],
                "calendar_integration": {},
                "services": []
            }
            self.extraction_schema = ExtractionSchema()
    
    async def handle(self):
        """Main entry point for handling the realtime call."""
        await self.websocket.accept()
        
        self._load_business()
        
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
            
            system_prompt = generate_system_prompt(self.business)
            
            session_update = {
                "type": "session.update",
                "session": {
                    "voice": "alloy",
                    "instructions": system_prompt,
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
            print(f"Session configured for business: {self.business.get('name')}")
            
            await asyncio.gather(
                self.receive_from_twilio(),
                self.receive_from_openai(),
                self.send_keepalive()
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
    
    async def send_keepalive(self):
        """Send periodic mark events to prevent Twilio timeout."""
        try:
            while True:
                await asyncio.sleep(30)
                if self.stream_sid:
                    mark_event = {
                        "event": "mark",
                        "streamSid": self.stream_sid,
                        "mark": {"name": "keepalive"}
                    }
                    try:
                        await self.websocket.send_text(json.dumps(mark_event))
                    except:
                        break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Keepalive error: {e}")
    
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
                    
                    if custom_params.get("business_id"):
                        try:
                            self.business_id = int(custom_params.get("business_id"))
                            self._load_business()
                        except:
                            pass
                    
                    print(f"Twilio stream started: {self.stream_sid}, Call SID: {self.call_sid}, Business: {self.business_id}")
                    
                    call_manager.start_call(self.call_sid, self.business_id, self.caller_number)
                    
                    try:
                        db = SessionLocal()
                        active_call = ActiveCall(
                            call_sid=self.call_sid,
                            business_id=self.business_id,
                            caller_number=self.caller_number,
                            status="in_progress"
                        )
                        db.add(active_call)
                        db.commit()
                        db.close()
                        print(f"ActiveCall created in database: {self.call_sid}")
                    except Exception as e:
                        print(f"Error creating ActiveCall: {e}")
                    universal_field_extractor.reset()
                    universal_field_extractor.extracted_data["phone"] = self.caller_number if self.caller_number != "Unknown" else None
                    
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
        """Process customer speech with universal intent detection and field extraction."""
        print(f"User said: {transcript}")
        self.transcripts.append({"speaker": "customer", "text": transcript})
        
        if self.call_sid:
            call_manager.add_transcript(self.call_sid, "customer", transcript)
        
        universal_field_extractor.extract_fields(
            transcript,
            schema=self.extraction_schema,
            existing_data=universal_field_extractor.extracted_data
        )
        
        conversation_history = [
            {"role": t["speaker"], "content": t["text"]}
            for t in self.transcripts[-10:]
        ]
        
        intent, confidence, metadata = universal_intent_engine.detect_intent(
            transcript,
            business_context=self.business,
            conversation_history=conversation_history
        )
        
        self.detected_intents.append({
            "intent": intent.value,
            "confidence": confidence,
            "metadata": metadata
        })
        
        print(f"Detected intent: {intent.value} (confidence: {confidence:.2f})")
        
        if intent == UniversalIntent.EMERGENCY:
            await self.handle_emergency()
        elif intent == UniversalIntent.BOOK_APPOINTMENT and not self.booking_in_progress:
            self.booking_in_progress = True
            await self.start_booking_flow()
        elif intent == UniversalIntent.CONFIRMATION and self.pending_slot:
            await self.confirm_booking()
        elif intent == UniversalIntent.REQUEST_QUOTE or intent == UniversalIntent.ASK_PRICING:
            await self.handle_pricing_request()
        elif intent == UniversalIntent.REQUEST_CALLBACK:
            await self.handle_callback_request()
        elif intent == UniversalIntent.RESCHEDULE:
            pass
        elif intent == UniversalIntent.CANCEL:
            pass
        elif intent == UniversalIntent.SPEAK_TO_HUMAN:
            pass
    
    async def handle_cortana_speech(self, transcript: str):
        """Track Cortana's responses."""
        print(f"Cortana said: {transcript}")
        self.transcripts.append({"speaker": "cortana", "text": transcript})
        
        if self.call_sid:
            call_manager.add_transcript(self.call_sid, "cortana", transcript)
    
    async def start_booking_flow(self):
        """Initialize the booking flow using universal appointment engine."""
        try:
            service_category = None
            if self.business.get("service_categories"):
                service_category = self.business["service_categories"][0]
            
            slots = universal_appointment_engine.get_available_slots(
                business=self.business,
                service_category=service_category,
                days_to_check=7
            )
            
            if slots:
                self.pending_slot = slots[0]
                print(f"Available slot: {self.pending_slot.start}")
                
        except Exception as e:
            print(f"Error getting availability: {e}")
    
    async def confirm_booking(self):
        """Confirm and create the booking using universal engines."""
        if not self.pending_slot:
            return
        
        try:
            customer_data = universal_field_extractor.to_customer_record()
            
            customer_record = await self._create_or_update_customer(customer_data)
            
            service_details = {
                "service_type": universal_field_extractor.extracted_data.get("service_category", "General Service"),
                "sub_service": universal_field_extractor.extracted_data.get("sub_service"),
                "urgency_level": universal_field_extractor.extracted_data.get("urgency", "normal"),
                "customer_notes": universal_field_extractor.extracted_data.get("job_details", "")
            }
            
            technician = await self._match_technician(service_details)
            
            result = universal_appointment_engine.book_appointment(
                business=self.business,
                customer=customer_data,
                slot=self.pending_slot,
                service_details=service_details,
                technician=technician
            )
            
            if result.success:
                self.confirmed_booking = {
                    "success": True,
                    "appointment_id": result.appointment_id,
                    "google_event_id": result.google_event_id,
                    "message": result.message
                }
                print(f"Booking confirmed: {result.message}")
                
                await self.send_confirmations(customer_data)
                
                if technician:
                    await self.dispatch_technician_universal(technician, customer_data, service_details)
            
            self.pending_slot = None
            
        except Exception as e:
            print(f"Booking error: {e}")
    
    async def handle_pricing_request(self):
        """Handle customer pricing/quote request - send email with quote."""
        try:
            customer_data = universal_field_extractor.to_customer_record()
            customer_email = customer_data.get("email")
            customer_name = customer_data.get("name", "Customer")
            customer_phone = customer_data.get("phone_number") or self.caller_number
            
            service_type = universal_field_extractor.extracted_data.get("service_category", "General Service")
            job_details = universal_field_extractor.extracted_data.get("job_details", "")
            
            industry = self.business.get("industry", "hvac") if self.business else "hvac"
            customer_data = universal_field_extractor.to_customer_record()
            quote = quote_generator.generate_quote(
                industry=industry,
                service_type=service_type,
                customer_data=customer_data,
                job_details={"description": job_details}
            )
            
            if customer_email:
                email_body = f"""
Hello {customer_name},

Thank you for your interest in {self.business.get('name', 'our services')}!

Here is your requested pricing information for {service_type}:

{quote.description if hasattr(quote, 'description') else 'Please contact us for a detailed quote.'}

Estimated Cost: ${quote.total if hasattr(quote, 'total') else 'Contact for quote'}

To schedule your service, please call us back or reply to this email.

Best regards,
{self.business.get('name', 'Our Team')}
"""
                email_service.send_email(
                    to_email=customer_email,
                    subject=f"Your Quote from {self.business.get('name', 'Our Company')}",
                    body_text=email_body
                )
                print(f"Quote email sent to: {customer_email}")
            else:
                if customer_phone and customer_phone != "Unknown":
                    business_name = self.business.get('name', 'us') if self.business else 'us'
                    quote_total = quote.total if hasattr(quote, 'total') else 'Contact for details'
                    dispatcher.send_sms(
                        customer_phone,
                        f"Thanks for calling {business_name}! Your estimated price for {service_type}: ${quote_total}. Reply for more info!"
                    )
                    print(f"Quote SMS sent to: {customer_phone}")
            
            print(f"Pricing request handled for {service_type}")
            
        except Exception as e:
            print(f"Pricing request error: {e}")
    
    async def handle_callback_request(self):
        """Schedule a callback for the customer."""
        try:
            customer_data = universal_field_extractor.to_customer_record()
            customer_phone = customer_data.get("phone_number") or self.caller_number
            customer_name = customer_data.get("name", "Customer")
            
            if customer_phone and customer_phone != "Unknown":
                from datetime import timedelta
                
                callback_request = OutboundCallRequest(
                    call_type=OutboundCallType.MISSED_CALL_FOLLOWUP,
                    customer_phone=customer_phone,
                    customer_name=customer_name,
                    business_id=self.business_id,
                    business_name=self.business.get("name", "Our Company"),
                    scheduled_time=datetime.now() + timedelta(minutes=5),
                    priority=9,
                    context={"reason": "customer_requested_callback"}
                )
                
                success = outbound_calling_engine.queue_call(callback_request)
                
                if success:
                    print(f"Callback scheduled for {customer_phone} in 5 minutes")
                    dispatcher.send_sms(
                        customer_phone,
                        f"We'll call you back in about 5 minutes! - {self.business.get('name', 'Our Team')}"
                    )
            else:
                print("No phone number available for callback")
            
        except Exception as e:
            print(f"Callback scheduling error: {e}")
    
    async def _create_or_update_customer(self, customer_data: dict) -> dict:
        """Create or update customer record in database."""
        try:
            db = SessionLocal()
            
            phone = customer_data.get("phone_number")
            existing = None
            if phone:
                existing = db.query(Customer).filter(
                    Customer.business_id == self.business_id,
                    Customer.phone_number == phone
                ).first()
            
            if existing:
                if customer_data.get("name"):
                    existing.name = customer_data["name"]
                if customer_data.get("email"):
                    existing.email = customer_data["email"]
                if customer_data.get("address"):
                    existing.address = customer_data["address"]
                existing.extra_data = {**(existing.extra_data or {}), **customer_data.get("extra_data", {})}
                existing.updated_at = datetime.utcnow()
                self.customer_id = existing.id
            else:
                new_customer = Customer(
                    business_id=self.business_id,
                    name=customer_data.get("name"),
                    phone_number=customer_data.get("phone_number"),
                    email=customer_data.get("email"),
                    address=customer_data.get("address"),
                    zip_code=customer_data.get("zip_code"),
                    extra_data=customer_data.get("extra_data", {}),
                    customer_type="lead",
                    source="phone"
                )
                db.add(new_customer)
                db.flush()
                self.customer_id = new_customer.id
            
            db.commit()
            db.close()
            
            return customer_data
            
        except Exception as e:
            print(f"Customer record error: {e}")
            return customer_data
    
    async def _match_technician(self, service_details: dict) -> dict:
        """Match best technician using universal dispatch engine."""
        try:
            db = SessionLocal()
            technicians = db.query(Technician).filter(
                Technician.business_id == self.business_id,
                Technician.is_available == True,
                Technician.status == "active"
            ).all()
            
            tech_list = [{
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "skills": t.skills or [],
                "home_zip": t.home_zip,
                "service_radius_miles": t.service_radius_miles or 25,
                "is_available": t.is_available,
                "status": t.status
            } for t in technicians]
            
            db.close()
            
            if not tech_list:
                return None
            
            dispatch_rules = self.business.get("dispatch_rules", {"mode": "skill_based"})
            
            job_requirements = {
                "service_type": service_details.get("service_type"),
                "required_skills": [service_details.get("service_type")] if service_details.get("service_type") else [],
                "urgency": service_details.get("urgency_level", "normal")
            }
            
            customer_location = {
                "zip_code": universal_field_extractor.extracted_data.get("zip_code")
            }
            
            best_match = universal_dispatch_engine.match_technician(
                technicians=tech_list,
                job_requirements=job_requirements,
                dispatch_rules=dispatch_rules,
                customer_location=customer_location
            )
            
            if best_match:
                return {
                    "id": best_match.technician_id,
                    "name": best_match.name,
                    "phone": best_match.phone,
                    "score": best_match.total_score,
                    "reasons": best_match.reasons
                }
            
            return tech_list[0] if tech_list else None
            
        except Exception as e:
            print(f"Technician matching error: {e}")
            return None
    
    async def send_confirmations(self, customer_data: dict):
        """Send SMS confirmation to customer."""
        phone = customer_data.get('phone_number') or self.caller_number
        if phone and phone != "Unknown":
            try:
                business_name = self.business.get("name", "Our Service Company")
                time_display = self.pending_slot.start.strftime("%B %d at %I:%M %p") if self.pending_slot else "As scheduled"
                
                dispatcher.send_customer_confirmation(
                    customer_phone=phone,
                    business_name=business_name,
                    appointment_time=time_display
                )
                print(f"Confirmation SMS sent to {phone}")
            except Exception as e:
                print(f"SMS confirmation error: {e}")
    
    async def dispatch_technician_universal(self, technician: dict, customer_data: dict, service_details: dict):
        """Dispatch technician using universal dispatch engine."""
        try:
            appointment = {
                "service_type": service_details.get("service_type", "Service Call"),
                "urgency_level": service_details.get("urgency_level", "normal"),
                "start_time": self.pending_slot.start if self.pending_slot else None,
                "customer_notes": service_details.get("customer_notes", "")
            }
            
            result = universal_dispatch_engine.dispatch_technician(
                technician=technician,
                appointment=appointment,
                customer=customer_data,
                business=self.business,
                dispatch_mode=self.business.get("dispatch_rules", {}).get("mode", "skill_based")
            )
            
            if result.get("status") == "sent":
                print(f"Technician {technician.get('name')} dispatched successfully")
            else:
                print(f"Dispatch result: {result}")
                
        except Exception as e:
            print(f"Dispatch error: {e}")
    
    async def handle_emergency(self):
        """Handle emergency dispatch using universal engines."""
        try:
            customer_data = universal_field_extractor.to_customer_record()
            
            db = SessionLocal()
            technicians = db.query(Technician).filter(
                Technician.business_id == self.business_id,
                Technician.is_available == True
            ).all()
            db.close()
            
            if technicians:
                tech_list = [{"name": t.name, "phone": t.phone, "is_available": t.is_available} for t in technicians]
                dispatcher.notify_emergency(tech_list, {
                    "customer_phone": customer_data.get('phone_number') or self.caller_number,
                    "issue": universal_field_extractor.extracted_data.get('job_details', 'Emergency service needed'),
                    "address": customer_data.get('address', 'To be confirmed')
                })
                print("Emergency dispatched to technicians")
        except Exception as e:
            print(f"Emergency dispatch error: {e}")
    
    async def cleanup(self):
        """Clean up resources and save call log with Phase 6 enhancements."""
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except:
                pass
        
        if self.call_sid and self.transcripts:
            try:
                customer_data = universal_field_extractor.to_customer_record()
                
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
                    customer_phone=customer_data.get('phone_number'),
                    customer_email=customer_data.get('email'),
                    customer_address=customer_data.get('address'),
                    booked_appointment=self.confirmed_booking is not None,
                    is_emergency=any(i["intent"] == "emergency" for i in self.detected_intents)
                )
                db.add(call_log)
                
                new_call = Call(
                    call_sid=self.call_sid,
                    business_id=self.business_id,
                    customer_id=self.customer_id,
                    caller_phone=self.caller_number,
                    start_time=datetime.utcnow(),
                    outcome="appointment_booked" if self.confirmed_booking else "lead_captured",
                    transcript=transcript_text,
                    extracted_fields=universal_field_extractor.extracted_data,
                    intents=self.detected_intents
                )
                db.add(new_call)
                
                db.commit()
                db.close()
                print(f"Call logs saved: {self.call_sid}")
            except Exception as e:
                print(f"Error saving call log: {e}")
        
        if self.call_sid:
            call_manager.end_call(self.call_sid)
            
            try:
                db = SessionLocal()
                active_call = db.query(ActiveCall).filter(
                    ActiveCall.call_sid == self.call_sid
                ).first()
                if active_call:
                    db.delete(active_call)
                    db.commit()
                    print(f"ActiveCall removed from database: {self.call_sid}")
                db.close()
            except Exception as e:
                print(f"Error removing ActiveCall: {e}")
        
        universal_field_extractor.reset()
        print("Realtime session ended")


async def handle_realtime_voice(websocket: WebSocket, business_id: int = None):
    """Entry point for realtime voice handling with optional business_id."""
    handler = RealtimeCallHandler(websocket, business_id)
    await handler.handle()
