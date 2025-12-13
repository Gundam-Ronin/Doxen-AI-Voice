from fastapi import APIRouter, Request, Depends, HTTPException, WebSocket
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
from datetime import datetime

from ..database.session import get_db
from ..database.models import Business, CallLog, ActiveCall
from ..core.call_manager import call_manager
from ..core.ai_engine import generate_ai_response, detect_language, detect_intent, analyze_sentiment
from ..core.vector_search import get_relevant_context
from ..core.routing import routing_manager
from ..core.dispatcher import dispatcher
from ..core.fallback import fallback_manager
from ..core.cortana_realtime import handle_realtime_voice

router = APIRouter(prefix="/twilio", tags=["twilio"])

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
async def handle_incoming_call(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    
    business = db.query(Business).filter(Business.phone_number == to_number).first()
    
    if not business:
        business = db.query(Business).first()
    
    if not business:
        twiml = generate_twiml_response(
            "Thank you for calling. We're currently not set up to take calls. Please try again later.",
            gather=False
        )
        return Response(content=twiml, media_type="application/xml")
    
    routing = routing_manager.get_routing_decision(
        business_hours=business.hours if business.hours else None,
        is_emergency=False,
        has_available_tech=True
    )
    
    call_manager.start_call(call_sid, business.id, from_number)
    
    active_call = ActiveCall(
        call_sid=call_sid,
        business_id=business.id,
        caller_number=from_number,
        status="in_progress"
    )
    db.add(active_call)
    db.commit()
    
    if routing["route"] == "after_hours":
        greeting = routing["message"]
    else:
        greeting = f"Thank you for calling {business.name}! I'm Cortana, your AI assistant. How can I help you today?"
    
    call_manager.add_transcript(call_sid, "cortana", greeting)
    
    twiml = generate_twiml_response(greeting)
    return Response(content=twiml, media_type="application/xml")

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
async def stream_twiml(request: Request):
    host = request.headers.get("host", "doxen-ai-voice--doxenstrategy.replit.app")
    ws_url = f"wss://{host}/twilio/realtime"
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please hold while we connect you to our AI assistant.</Say>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/realtime")
async def realtime_audio(ws: WebSocket):
    await handle_realtime_voice(ws)
