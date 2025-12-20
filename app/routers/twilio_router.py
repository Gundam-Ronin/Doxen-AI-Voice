from fastapi import APIRouter, Request, Depends, HTTPException, WebSocket
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import asyncio
from datetime import datetime

from ..database.session import get_db, get_db_optional
from ..database.models import Business, CallLog, ActiveCall
from ..core.call_manager import call_manager
from ..core.ai_engine import generate_ai_response, detect_language, detect_intent, analyze_sentiment
from ..core.vector_search import get_relevant_context
from ..core.routing import routing_manager
from ..core.dispatcher import dispatcher
from ..core.fallback import fallback_manager
from ..core.cortana_realtime import handle_realtime_voice

router = APIRouter(prefix="/twilio", tags=["twilio"])

@router.post("/test")
async def test_voice():
    """Simple test endpoint - no WebSocket, just TTS."""
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Hello! This is a test. Your connection to the Cortana AI Voice System is working correctly. Goodbye!</Say>
</Response>"""
    return Response(content=twiml, media_type="application/xml")

@router.post("/stream-test")
async def stream_test_twiml(request: Request):
    """Test endpoint with stream - just plays a message, no OpenAI."""
    host = request.headers.get("host", "doxen-ai-voice--doxenstrategy.replit.app")
    print(f"[STREAM-TEST] Incoming call, host: {host}")
    
    # Use hardcoded URL to avoid any hostname issues
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Welcome! Connecting you to the stream now.</Say>
    <Pause length="1"/>
    <Connect>
        <Stream url="wss://doxen-ai-voice--doxenstrategy.replit.app/twilio/realtime-test" />
    </Connect>
    <Say voice="Polly.Joanna">The stream has ended. Thank you for calling.</Say>
</Response>"""
    return Response(content=twiml, media_type="application/xml")

@router.websocket("/realtime-test")
async def realtime_test(ws: WebSocket):
    """Simple WebSocket that just acknowledges connection then closes after 3 seconds."""
    print("[REALTIME-TEST] WebSocket connection attempt")
    print(f"[REALTIME-TEST] Headers: {dict(ws.headers)}")
    
    # Check if Twilio requested a subprotocol
    requested_protocol = ws.headers.get("sec-websocket-protocol", "")
    print(f"[REALTIME-TEST] Requested subprotocol: '{requested_protocol}'")
    
    if "audio.twilio.com" in requested_protocol:
        await ws.accept(subprotocol="audio.twilio.com")
        print("[REALTIME-TEST] WebSocket accepted WITH subprotocol")
    else:
        await ws.accept()
        print("[REALTIME-TEST] WebSocket accepted WITHOUT subprotocol")
    
    stream_sid = None
    
    try:
        # Wait for start event
        data = await ws.receive_text()
        msg = json.loads(data)
        
        if msg.get("event") == "start":
            stream_sid = msg["start"]["streamSid"]
            print(f"[REALTIME-TEST] Stream started: {stream_sid}")
        
        # Wait 3 seconds then close - this should trigger the final <Say>
        await asyncio.sleep(3)
        print("[REALTIME-TEST] Closing connection after 3 seconds")
        await ws.close()
                
    except Exception as e:
        print(f"[REALTIME-TEST] Error: {e}")
    finally:
        print("[REALTIME-TEST] Handler finished")

def generate_twiml_response(message: str, gather: bool = True) -> str:
    if gather:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" timeout="5" speechTimeout="auto" action="/twilio/voice/continue" method="POST">
        <Say voice="Polly.Joanna">{message}</Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear anything. Goodbye!</Say>
</Response>"""
    else:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{message}</Say>
</Response>"""

@router.post("/voice")
async def handle_incoming_call(request: Request, db: Session = Depends(get_db_optional)):
    """Main voice webhook - returns TwiML to connect to Realtime AI stream."""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "unknown")
        from_number = form_data.get("From", "Unknown")
        to_number = form_data.get("To", "")
        
        print(f"[TWILIO VOICE] Incoming call from {from_number}, CallSID: {call_sid}")
        
        business_id = 1
        business_name = "our company"
        
        if db:
            try:
                business = db.query(Business).filter(Business.phone_number == to_number).first()
                if not business:
                    business = db.query(Business).first()
                if business:
                    business_id = business.id
                    business_name = business.name
            except Exception as db_err:
                print(f"[TWILIO VOICE] Database query error: {db_err}")
        
        # Track the call (non-blocking)
        try:
            call_manager.start_call(call_sid, business_id, from_number)
            
            if db:
                active_call = ActiveCall(
                    call_sid=call_sid,
                    business_id=business_id,
                    caller_number=from_number,
                    status="in_progress"
                )
                db.add(active_call)
                db.commit()
        except Exception as e:
            print(f"[TWILIO VOICE] Error tracking call: {e}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
        
        # Use hardcoded production URL for the WebSocket stream
        ws_url = "wss://doxen-ai-voice--doxenstrategy.replit.app/twilio/realtime"
        
        # Return TwiML that connects to the Realtime AI stream
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {business_name}. Please hold while I connect you to our AI assistant.</Say>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="from" value="{from_number}" />
            <Parameter name="business_id" value="{business_id}" />
            <Parameter name="call_sid" value="{call_sid}" />
        </Stream>
    </Connect>
    <Say voice="Polly.Joanna">I apologize, but we're experiencing technical difficulties. Please try calling back later.</Say>
</Response>"""
        
        print(f"[TWILIO VOICE] Returning TwiML with stream URL: {ws_url}")
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"[TWILIO VOICE] Critical error: {e}")
        import traceback
        traceback.print_exc()
        # Return basic TwiML even on error
        fallback_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling. Please hold while I connect you.</Say>
    <Connect>
        <Stream url="wss://doxen-ai-voice--doxenstrategy.replit.app/twilio/realtime">
            <Parameter name="from" value="Unknown" />
            <Parameter name="business_id" value="1" />
            <Parameter name="call_sid" value="unknown" />
        </Stream>
    </Connect>
</Response>"""
        return Response(content=fallback_twiml, media_type="application/xml")

@router.post("/voice/continue")
async def continue_call(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    speech_result = form_data.get("SpeechResult", "")
    
    if not speech_result:
        twiml = generate_twiml_response("I didn't quite catch that. Could you please repeat?")
        return Response(content=twiml, media_type="application/xml")
    
    call_data = call_manager.get_call(call_sid)
    if not call_data:
        twiml = generate_twiml_response(
            "I'm sorry, there was an issue with your call. Please call back.",
            gather=False
        )
        return Response(content=twiml, media_type="application/xml")
    
    business_id = call_data["business_id"]
    business = db.query(Business).filter(Business.id == business_id).first()
    
    call_manager.add_transcript(call_sid, "customer", speech_result)
    
    language = detect_language(speech_result)
    intent = detect_intent(speech_result)
    
    if intent["is_emergency"]:
        from ..database.models import Technician
        techs = db.query(Technician).filter(
            Technician.business_id == business_id,
            Technician.is_available == True
        ).all()
        
        if techs:
            tech_list = [{"name": t.name, "phone": t.phone, "is_available": t.is_available} for t in techs]
            dispatcher.notify_emergency(tech_list, {
                "customer_phone": call_data["caller_number"],
                "issue": speech_result
            })
    
    kb_context = get_relevant_context(speech_result, business_id)
    
    business_context = {
        "name": business.name if business else "our company",
        "services": business.services if business else [],
        "pricing": business.pricing if business else {},
        "hours": business.hours if business else {},
        "location": business.location if business else ""
    }
    
    conversation_history = call_manager.get_conversation_history(call_sid)
    
    if not fallback_manager.is_service_healthy("openai"):
        fallback = fallback_manager.get_fallback_response("openai")
        ai_response = fallback["tts_text"]
    else:
        try:
            ai_response = await generate_ai_response(
                user_message=speech_result,
                business_context=business_context,
                conversation_history=conversation_history,
                knowledgebase_context=kb_context,
                personality=business.ai_personality if business else "friendly and professional"
            )
        except Exception as e:
            fallback_manager.record_error("openai", str(e))
            fallback = fallback_manager.get_fallback_response("openai")
            ai_response = fallback["tts_text"]
    
    call_manager.add_transcript(call_sid, "cortana", ai_response)
    
    goodbye_indicators = ["goodbye", "bye", "that's all", "thank you", "thanks", "have a nice day"]
    should_end = any(indicator in speech_result.lower() for indicator in goodbye_indicators)
    
    if should_end:
        closing = "Thank you for calling! Have a wonderful day. Goodbye!"
        call_manager.add_transcript(call_sid, "cortana", closing)
        twiml = generate_twiml_response(closing, gather=False)
        
        call_data = call_manager.end_call(call_sid)
        if call_data:
            transcript_text = "\n".join([
                f"{t['speaker']}: {t['text']}" for t in call_data.get("transcript", [])
            ])
            
            call_log = CallLog(
                business_id=business_id,
                call_sid=call_sid,
                caller_number=call_data["caller_number"],
                transcript=transcript_text,
                sentiment=analyze_sentiment(transcript_text),
                disposition="completed",
                booked_appointment=intent.get("wants_appointment", False),
                is_emergency=intent.get("is_emergency", False),
                language=language
            )
            db.add(call_log)
            
            db.query(ActiveCall).filter(ActiveCall.call_sid == call_sid).delete()
            db.commit()
    else:
        twiml = generate_twiml_response(ai_response)
    
    return Response(content=twiml, media_type="application/xml")

@router.post("/status")
async def call_status(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    
    if call_status in ["completed", "failed", "busy", "no-answer"]:
        call_data = call_manager.end_call(call_sid)
        db.query(ActiveCall).filter(ActiveCall.call_sid == call_sid).delete()
        db.commit()
    
    return {"status": "ok"}

@router.post("/sms")
async def handle_sms(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "").strip().upper()
    
    if body == "ACCEPT":
        response_msg = "You have accepted the dispatch. Please proceed to the customer location."
    elif body == "YES":
        response_msg = "Confirmed! Thank you for accepting the job."
    elif body == "CANCEL":
        response_msg = "Your appointment has been noted for cancellation. A team member will contact you shortly."
    elif body == "HELP":
        response_msg = "For assistance, please call our office directly or reply with your question."
    else:
        response_msg = "Thank you for your message. A team member will review and respond shortly."
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_msg}</Message>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


@router.post("/stream")
async def stream_twiml(request: Request, db: Session = Depends(get_db_optional)):
    try:
        form_data = await request.form()
        from_number = form_data.get("From", "Unknown")
        to_number = form_data.get("To", "")
        call_sid = form_data.get("CallSid", "")
        
        business_id = 1
        try:
            business = db.query(Business).filter(Business.phone_number == to_number).first()
            if not business:
                business = db.query(Business).first()
            business_id = business.id if business else 1
        except Exception as db_err:
            print(f"[TWILIO STREAM] Database error: {db_err}")
        
        # Use hardcoded production URL to avoid any host header issues
        ws_url = "wss://doxen-ai-voice--doxenstrategy.replit.app/twilio/realtime"
        
        print(f"[TWILIO STREAM] Call from {from_number}, CallSID: {call_sid}, Business: {business_id}")
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling. Please hold while I connect you to our AI assistant.</Say>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="from" value="{from_number}" />
            <Parameter name="business_id" value="{business_id}" />
            <Parameter name="call_sid" value="{call_sid}" />
        </Stream>
    </Connect>
    <Say voice="Polly.Joanna">I apologize, but we're experiencing technical difficulties. Please try calling back later or leave a message.</Say>
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"[TWILIO STREAM] Error: {e}")
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling. Please hold while we connect you.</Say>
    <Connect>
        <Stream url="wss://doxen-ai-voice--doxenstrategy.replit.app/twilio/realtime">
            <Parameter name="from" value="Unknown" />
            <Parameter name="business_id" value="1" />
            <Parameter name="call_sid" value="unknown" />
        </Stream>
    </Connect>
</Response>"""
        return Response(content=error_twiml, media_type="application/xml")


@router.websocket("/realtime")
async def realtime_audio(ws: WebSocket):
    try:
        print("[REALTIME WS] WebSocket connection attempt")
        print(f"[REALTIME WS] Headers: {dict(ws.headers)}")
        
        # Check if Twilio requested a subprotocol
        requested_protocol = ws.headers.get("sec-websocket-protocol", "")
        print(f"[REALTIME WS] Requested subprotocol: '{requested_protocol}'")
        
        if "audio.twilio.com" in requested_protocol:
            await ws.accept(subprotocol="audio.twilio.com")
            print("[REALTIME WS] WebSocket accepted WITH subprotocol audio.twilio.com")
        else:
            await ws.accept()
            print("[REALTIME WS] WebSocket accepted WITHOUT subprotocol")
        
        await handle_realtime_voice(ws, already_accepted=True)
        print("[REALTIME WS] Handler completed normally")
    except Exception as e:
        print(f"[REALTIME WS] Error in handler: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ws.close(code=1011, reason="Internal server error")
        except:
            pass
