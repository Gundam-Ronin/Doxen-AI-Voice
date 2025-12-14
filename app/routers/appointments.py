from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from ..database.session import get_db
from ..database.models import Business, Technician, CallLog
from ..core.calendar import calendar_service
from ..core.dispatcher import dispatcher

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

class AppointmentRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    service_type: str
    preferred_time: str
    duration_minutes: Optional[int] = 60
    notes: Optional[str] = None
    is_emergency: Optional[bool] = False
    technician_id: Optional[int] = None
    urgency: Optional[str] = "normal"

class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    service_requested: Optional[str] = None

class CallStoreRequest(BaseModel):
    call_sid: str
    business_id: int
    caller_number: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = "neutral"
    disposition: Optional[str] = "completed"
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    service_requested: Optional[str] = None
    booked_appointment: Optional[bool] = False
    is_emergency: Optional[bool] = False
    language: Optional[str] = "en"

class TechnicianAssignRequest(BaseModel):
    call_id: int
    technician_id: int
    notify: Optional[bool] = True

@router.get("/availability/{business_id}")
async def get_availability(
    business_id: int,
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    slots = await calendar_service.get_availability(
        days_ahead=days_ahead,
        slot_duration_minutes=60
    )
    
    return {
        "business_id": business_id,
        "business_name": business.name,
        "available_slots": slots,
        "count": len(slots)
    }

@router.get("/checkAvailability")
async def check_availability(
    business_id: int = 1,
    date: Optional[str] = None,
    days_ahead: int = 7
):
    slots = await calendar_service.get_availability(
        days_ahead=days_ahead,
        slot_duration_minutes=60
    )
    
    if date:
        slots = [s for s in slots if date in s.get("start", "")]
    
    return {
        "available": len(slots) > 0,
        "slots": slots,
        "next_available": slots[0] if slots else None
    }

@router.post("/create")
async def create_appointment(
    appointment: AppointmentRequest,
    business_id: int = 1,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    tech = None
    if appointment.technician_id:
        tech = db.query(Technician).filter(
            Technician.id == appointment.technician_id,
            Technician.business_id == business_id
        ).first()
    else:
        tech = db.query(Technician).filter(
            Technician.business_id == business_id,
            Technician.is_available == True
        ).first()
    
    summary = f"{appointment.service_type} - {appointment.customer_name or 'Customer'}"
    description = f"""
Service: {appointment.service_type}
Customer: {appointment.customer_name or 'N/A'}
Phone: {appointment.customer_phone}
Address: {appointment.customer_address or 'N/A'}
Email: {appointment.customer_email or 'N/A'}
Notes: {appointment.notes or 'None'}
Urgency: {appointment.urgency}
Emergency: {'Yes' if appointment.is_emergency else 'No'}
"""
    
    customer_info = {
        "name": appointment.customer_name,
        "phone": appointment.customer_phone,
        "email": appointment.customer_email,
        "address": appointment.customer_address
    }
    
    result = await calendar_service.book_appointment(
        summary=summary,
        description=description,
        start_time=appointment.preferred_time,
        duration_minutes=appointment.duration_minutes,
        attendee_email=appointment.customer_email,
        customer_info=customer_info
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to book appointment")
    
    try:
        formatted_time = datetime.fromisoformat(appointment.preferred_time).strftime("%A, %B %d at %I:%M %p")
    except:
        formatted_time = appointment.preferred_time
    
    if tech:
        dispatcher.dispatch_technician(
            technician_name=tech.name,
            technician_phone=tech.phone,
            customer_info=customer_info,
            appointment_time=formatted_time,
            service_type=appointment.service_type,
            is_emergency=appointment.is_emergency
        )
        
        dispatcher.send_customer_confirmation(
            customer_phone=appointment.customer_phone,
            business_name=business.name,
            appointment_time=formatted_time,
            technician_name=tech.name
        )
    
    return {
        "success": True,
        "event_id": result.get("event_id"),
        "appointment_time": appointment.preferred_time,
        "formatted_time": formatted_time,
        "technician": tech.name if tech else None,
        "message": "Appointment created successfully"
    }

@router.post("/book/{business_id}")
async def book_appointment(
    business_id: int,
    appointment: AppointmentRequest,
    db: Session = Depends(get_db)
):
    return await create_appointment(appointment, business_id, db)

@router.get("/upcoming/{business_id}")
async def get_upcoming_appointments(
    business_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    
    appointments = db.query(CallLog).filter(
        CallLog.business_id == business_id,
        CallLog.booked_appointment == True,
        CallLog.appointment_time >= now
    ).order_by(CallLog.appointment_time).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "caller_number": a.caller_number,
            "customer_name": a.customer_name,
            "customer_phone": a.customer_phone,
            "appointment_time": a.appointment_time.isoformat() if a.appointment_time else None,
            "is_emergency": a.is_emergency,
            "summary": a.summary,
            "assigned_tech_id": a.assigned_tech_id
        }
        for a in appointments
    ]

@router.post("/cancel/{appointment_id}")
async def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    call_log = db.query(CallLog).filter(CallLog.id == appointment_id).first()
    
    if not call_log:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    call_log.booked_appointment = False
    call_log.disposition = "cancelled"
    db.commit()
    
    return {"success": True, "message": "Appointment cancelled successfully"}


@router.post("/customer/update/{call_id}")
async def update_customer(
    call_id: int,
    update: CustomerUpdate,
    db: Session = Depends(get_db)
):
    call_log = db.query(CallLog).filter(CallLog.id == call_id).first()
    
    if not call_log:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(call_log, key, value)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Customer information updated",
        "call_id": call_id
    }


@router.post("/calls/store")
async def store_call(
    call_data: CallStoreRequest,
    db: Session = Depends(get_db)
):
    existing = db.query(CallLog).filter(CallLog.call_sid == call_data.call_sid).first()
    
    if existing:
        for key, value in call_data.dict().items():
            if value is not None and key != "call_sid":
                setattr(existing, key, value)
        db.commit()
        return {"success": True, "message": "Call log updated", "id": existing.id}
    
    call_log = CallLog(
        business_id=call_data.business_id,
        call_sid=call_data.call_sid,
        caller_number=call_data.caller_number,
        transcript=call_data.transcript,
        summary=call_data.summary,
        sentiment=call_data.sentiment,
        disposition=call_data.disposition,
        customer_name=call_data.customer_name,
        customer_phone=call_data.customer_phone,
        customer_email=call_data.customer_email,
        customer_address=call_data.customer_address,
        service_requested=call_data.service_requested,
        booked_appointment=call_data.booked_appointment,
        is_emergency=call_data.is_emergency,
        language=call_data.language
    )
    db.add(call_log)
    db.commit()
    db.refresh(call_log)
    
    return {"success": True, "message": "Call log stored", "id": call_log.id}


@router.post("/technician/assign")
async def assign_technician(
    assignment: TechnicianAssignRequest,
    db: Session = Depends(get_db)
):
    call_log = db.query(CallLog).filter(CallLog.id == assignment.call_id).first()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    tech = db.query(Technician).filter(Technician.id == assignment.technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    call_log.assigned_tech_id = assignment.technician_id
    db.commit()
    
    if assignment.notify and tech.phone:
        customer_info = {
            "name": call_log.customer_name or "Customer",
            "phone": call_log.customer_phone or call_log.caller_number,
            "address": call_log.customer_address or "To be confirmed"
        }
        
        appointment_time = call_log.appointment_time.strftime("%A, %B %d at %I:%M %p") if call_log.appointment_time else "ASAP"
        
        dispatcher.dispatch_technician(
            technician_name=tech.name,
            technician_phone=tech.phone,
            customer_info=customer_info,
            appointment_time=appointment_time,
            service_type=call_log.service_requested or "Service call",
            is_emergency=call_log.is_emergency
        )
    
    return {
        "success": True,
        "message": f"Technician {tech.name} assigned to call",
        "technician_id": tech.id,
        "call_id": call_log.id
    }


@router.get("/technician/match/{business_id}")
async def match_technician(
    business_id: int,
    service_type: Optional[str] = None,
    is_emergency: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Technician).filter(
        Technician.business_id == business_id,
        Technician.is_available == True
    )
    
    technicians = query.all()
    
    if not technicians:
        return {"matched": False, "technician": None, "message": "No available technicians"}
    
    matched_tech = technicians[0]
    
    if service_type:
        for tech in technicians:
            if tech.skills and service_type.lower() in [s.lower() for s in tech.skills]:
                matched_tech = tech
                break
    
    return {
        "matched": True,
        "technician": {
            "id": matched_tech.id,
            "name": matched_tech.name,
            "phone": matched_tech.phone,
            "skills": matched_tech.skills
        }
    }
