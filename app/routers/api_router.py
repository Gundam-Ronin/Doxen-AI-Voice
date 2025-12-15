from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database.session import get_db
from ..database.models import Business, Technician, CallLog, Call, Appointment
from ..core.fallback import fallback_manager

router = APIRouter(prefix="/api", tags=["api"])

class BusinessCreate(BaseModel):
    owner_id: str
    name: str
    phone_number: Optional[str] = None
    location: Optional[str] = None
    hours: Optional[dict] = None
    services: Optional[list] = None
    pricing: Optional[dict] = None
    ai_personality: Optional[str] = "friendly and professional"

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    hours: Optional[dict] = None
    services: Optional[list] = None
    pricing: Optional[dict] = None
    ai_personality: Optional[str] = None

class TechnicianCreate(BaseModel):
    name: str
    phone: str
    role: Optional[str] = "technician"
    skills: Optional[list] = None

class TechnicianUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_available: Optional[bool] = None
    skills: Optional[list] = None

@router.get("/businesses")
async def list_businesses(db: Session = Depends(get_db)):
    businesses = db.query(Business).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "phone_number": b.phone_number,
            "location": b.location,
            "subscription_status": b.subscription_status,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in businesses
    ]

@router.get("/businesses/{business_id}")
async def get_business(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "id": business.id,
        "owner_id": business.owner_id,
        "name": business.name,
        "phone_number": business.phone_number,
        "location": business.location,
        "hours": business.hours,
        "services": business.services,
        "pricing": business.pricing,
        "ai_personality": business.ai_personality,
        "subscription_status": business.subscription_status,
        "created_at": business.created_at.isoformat() if business.created_at else None
    }

@router.post("/businesses")
async def create_business(business: BusinessCreate, db: Session = Depends(get_db)):
    new_business = Business(
        owner_id=business.owner_id,
        name=business.name,
        phone_number=business.phone_number,
        location=business.location,
        hours=business.hours or {},
        services=business.services or [],
        pricing=business.pricing or {},
        ai_personality=business.ai_personality
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    
    return {"id": new_business.id, "name": new_business.name, "message": "Business created successfully"}

@router.put("/businesses/{business_id}")
async def update_business(business_id: int, update: BusinessUpdate, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business, key, value)
    
    business.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Business updated successfully"}

@router.get("/businesses/{business_id}/technicians")
async def list_technicians(business_id: int, db: Session = Depends(get_db)):
    technicians = db.query(Technician).filter(Technician.business_id == business_id).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "phone": t.phone,
            "role": t.role,
            "is_available": t.is_available,
            "skills": t.skills
        }
        for t in technicians
    ]

@router.post("/businesses/{business_id}/technicians")
async def create_technician(business_id: int, tech: TechnicianCreate, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    new_tech = Technician(
        business_id=business_id,
        name=tech.name,
        phone=tech.phone,
        role=tech.role,
        skills=tech.skills or []
    )
    db.add(new_tech)
    db.commit()
    db.refresh(new_tech)
    
    return {"id": new_tech.id, "name": new_tech.name, "message": "Technician added successfully"}

@router.put("/technicians/{tech_id}")
async def update_technician(tech_id: int, update: TechnicianUpdate, db: Session = Depends(get_db)):
    tech = db.query(Technician).filter(Technician.id == tech_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tech, key, value)
    
    db.commit()
    
    return {"message": "Technician updated successfully"}

@router.delete("/technicians/{tech_id}")
async def delete_technician(tech_id: int, db: Session = Depends(get_db)):
    tech = db.query(Technician).filter(Technician.id == tech_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    db.delete(tech)
    db.commit()
    
    return {"message": "Technician deleted successfully"}

@router.get("/businesses/{business_id}/calls")
async def list_calls(
    business_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    legacy_calls = db.query(CallLog).filter(
        CallLog.business_id == business_id
    ).order_by(CallLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    new_calls = db.query(Call).filter(
        Call.business_id == business_id
    ).order_by(Call.start_time.desc()).offset(offset).limit(limit).all()
    
    results = []
    for c in legacy_calls:
        results.append({
            "id": c.id,
            "source": "legacy",
            "call_sid": c.call_sid,
            "caller_number": c.caller_number,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "duration": c.duration,
            "summary": c.summary,
            "sentiment": c.sentiment,
            "disposition": c.disposition,
            "booked_appointment": c.booked_appointment,
            "is_emergency": c.is_emergency,
            "language": c.language
        })
    
    for c in new_calls:
        is_emergency = any(i.get("intent") == "emergency" for i in (c.intents or []))
        is_booked = c.outcome == "appointment_booked" or any(i.get("intent") == "book_appointment" for i in (c.intents or []))
        results.append({
            "id": c.id,
            "source": "phase6",
            "call_sid": c.call_sid,
            "caller_number": c.caller_phone,
            "timestamp": c.start_time.isoformat() if c.start_time else None,
            "duration": c.duration_seconds,
            "summary": c.call_summary,
            "sentiment": c.sentiment,
            "disposition": c.outcome,
            "booked_appointment": is_booked,
            "is_emergency": is_emergency,
            "intents": c.intents,
            "extracted_fields": c.extracted_fields
        })
    
    results.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return results[:limit]

@router.get("/calls/{call_id}")
async def get_call_details(call_id: int, db: Session = Depends(get_db)):
    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": call.id,
        "call_sid": call.call_sid,
        "caller_number": call.caller_number,
        "timestamp": call.timestamp.isoformat() if call.timestamp else None,
        "duration": call.duration,
        "transcript": call.transcript,
        "summary": call.summary,
        "sentiment": call.sentiment,
        "disposition": call.disposition,
        "booked_appointment": call.booked_appointment,
        "appointment_time": call.appointment_time.isoformat() if call.appointment_time else None,
        "is_emergency": call.is_emergency,
        "language": call.language
    }

@router.get("/health")
async def health_check():
    return fallback_manager.get_health_status()

@router.get("/stats/{business_id}")
async def get_business_stats(business_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import func
    from datetime import timedelta
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    legacy_total = db.query(func.count(CallLog.id)).filter(CallLog.business_id == business_id).scalar() or 0
    new_total = db.query(func.count(Call.id)).filter(Call.business_id == business_id).scalar() or 0
    total_calls = legacy_total + new_total
    
    legacy_weekly = db.query(func.count(CallLog.id)).filter(
        CallLog.business_id == business_id, CallLog.timestamp >= week_ago
    ).scalar() or 0
    new_weekly = db.query(func.count(Call.id)).filter(
        Call.business_id == business_id, Call.start_time >= week_ago
    ).scalar() or 0
    weekly_calls = legacy_weekly + new_weekly
    
    legacy_monthly = db.query(func.count(CallLog.id)).filter(
        CallLog.business_id == business_id, CallLog.timestamp >= month_ago
    ).scalar() or 0
    new_monthly = db.query(func.count(Call.id)).filter(
        Call.business_id == business_id, Call.start_time >= month_ago
    ).scalar() or 0
    monthly_calls = legacy_monthly + new_monthly
    
    legacy_appointments = db.query(func.count(CallLog.id)).filter(
        CallLog.business_id == business_id, CallLog.booked_appointment == True, CallLog.timestamp >= month_ago
    ).scalar() or 0
    new_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.business_id == business_id, Appointment.start_time >= month_ago
    ).scalar() or 0
    appointments_booked = legacy_appointments + new_appointments
    
    legacy_emergencies = db.query(func.count(CallLog.id)).filter(
        CallLog.business_id == business_id, CallLog.is_emergency == True, CallLog.timestamp >= month_ago
    ).scalar() or 0
    emergencies = legacy_emergencies
    
    conversion_rate = (appointments_booked / monthly_calls * 100) if monthly_calls > 0 else 0
    
    return {
        "total_calls": total_calls,
        "weekly_calls": weekly_calls,
        "monthly_calls": monthly_calls,
        "appointments_booked": appointments_booked,
        "emergencies": emergencies,
        "conversion_rate": round(conversion_rate, 1)
    }
