from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
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
    service_type: str
    preferred_time: str
    duration_minutes: Optional[int] = 60
    notes: Optional[str] = None
    is_emergency: Optional[bool] = False
    technician_id: Optional[int] = None

@router.get("/availability/{business_id}")
async def get_availability(
    business_id: int,
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    slots = calendar_service.get_availability(
        days_ahead=days_ahead,
        slot_duration_minutes=60
    )
    
    return {
        "business_id": business_id,
        "business_name": business.name,
        "available_slots": slots
    }

@router.post("/book/{business_id}")
async def book_appointment(
    business_id: int,
    appointment: AppointmentRequest,
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
Notes: {appointment.notes or 'None'}
Emergency: {'Yes' if appointment.is_emergency else 'No'}
"""
    
    result = calendar_service.book_appointment(
        summary=summary,
        description=description,
        start_time=appointment.preferred_time,
        duration_minutes=appointment.duration_minutes,
        attendee_email=appointment.customer_email
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to book appointment")
    
    if tech:
        try:
            formatted_time = datetime.fromisoformat(appointment.preferred_time).strftime("%A, %B %d at %I:%M %p")
        except:
            formatted_time = appointment.preferred_time
        
        dispatcher.dispatch_technician(
            technician_name=tech.name,
            technician_phone=tech.phone,
            customer_info={
                "name": appointment.customer_name,
                "phone": appointment.customer_phone
            },
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
        "technician": tech.name if tech else None,
        "message": "Appointment booked successfully"
    }

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
            "appointment_time": a.appointment_time.isoformat() if a.appointment_time else None,
            "is_emergency": a.is_emergency,
            "summary": a.summary
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
    
    return {"message": "Appointment cancelled successfully"}
