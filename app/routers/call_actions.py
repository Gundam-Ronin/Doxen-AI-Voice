from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ..database.session import get_db
from ..database.models import CallLog, Technician, ActiveCall
from ..core.dispatcher import dispatcher
from ..core.technician_matcher import technician_matcher

router = APIRouter(prefix="/api/call-actions", tags=["call-actions"])


class ForceAssignRequest(BaseModel):
    call_id: int
    technician_id: int
    notify_technician: bool = True
    notify_customer: bool = True

class OverrideDecisionRequest(BaseModel):
    call_id: int
    override_type: str
    new_value: str
    reason: Optional[str] = None

class CancelJobRequest(BaseModel):
    call_id: int
    reason: Optional[str] = None
    notify_customer: bool = True
    notify_technician: bool = True


@router.post("/force-assign")
async def force_assign_technician(
    request: ForceAssignRequest,
    db: Session = Depends(get_db)
):
    call = db.query(CallLog).filter(CallLog.id == request.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    tech = db.query(Technician).filter(Technician.id == request.technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    old_tech_id = call.assigned_tech_id
    call.assigned_tech_id = request.technician_id
    db.commit()
    
    if request.notify_technician:
        customer_info = {
            "name": call.customer_name or "Customer",
            "phone": call.customer_phone or call.caller_number,
            "address": call.customer_address or "To be confirmed"
        }
        
        appointment_time = "ASAP"
        if call.appointment_time:
            appointment_time = call.appointment_time.strftime("%A, %B %d at %I:%M %p")
        
        dispatcher.dispatch_technician(
            technician_name=tech.name,
            technician_phone=tech.phone,
            customer_info=customer_info,
            appointment_time=appointment_time,
            service_type=call.service_requested or "Service call",
            is_emergency=call.is_emergency or False
        )
    
    return {
        "success": True,
        "message": f"Technician {tech.name} force assigned to call",
        "previous_tech_id": old_tech_id,
        "new_tech_id": request.technician_id
    }


@router.post("/cancel-job")
async def cancel_job(
    request: CancelJobRequest,
    db: Session = Depends(get_db)
):
    call = db.query(CallLog).filter(CallLog.id == request.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    call.disposition = "cancelled"
    call.booked_appointment = False
    
    if request.reason:
        existing_summary = call.summary or ""
        call.summary = f"{existing_summary}\n[CANCELLED: {request.reason}]"
    
    db.commit()
    
    if request.notify_customer and call.customer_phone:
        dispatcher.send_sms(
            call.customer_phone,
            f"Your appointment has been cancelled. Reason: {request.reason or 'Schedule change'}. Please call us to reschedule."
        )
    
    if request.notify_technician and call.assigned_tech_id:
        tech = db.query(Technician).filter(Technician.id == call.assigned_tech_id).first()
        if tech:
            dispatcher.send_sms(
                tech.phone,
                f"Job cancelled for {call.customer_name or 'customer'}. Reason: {request.reason or 'Schedule change'}"
            )
    
    return {
        "success": True,
        "message": "Job cancelled successfully",
        "call_id": request.call_id
    }


@router.post("/override-decision")
async def override_ai_decision(
    request: OverrideDecisionRequest,
    db: Session = Depends(get_db)
):
    call = db.query(CallLog).filter(CallLog.id == request.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    valid_overrides = {
        "disposition": ["completed", "cancelled", "rescheduled", "no-show", "follow-up"],
        "sentiment": ["positive", "neutral", "negative"],
        "is_emergency": ["true", "false"],
        "booked_appointment": ["true", "false"]
    }
    
    if request.override_type not in valid_overrides:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid override type. Valid types: {list(valid_overrides.keys())}"
        )
    
    if request.new_value.lower() not in [v.lower() for v in valid_overrides[request.override_type]]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {request.override_type}. Valid values: {valid_overrides[request.override_type]}"
        )
    
    old_value = getattr(call, request.override_type)
    
    if request.override_type in ["is_emergency", "booked_appointment"]:
        new_val = request.new_value.lower() == "true"
        setattr(call, request.override_type, new_val)
    else:
        setattr(call, request.override_type, request.new_value)
    
    if request.reason:
        existing_summary = call.summary or ""
        call.summary = f"{existing_summary}\n[OVERRIDE {request.override_type}: {old_value} -> {request.new_value}. Reason: {request.reason}]"
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Override applied: {request.override_type} changed from {old_value} to {request.new_value}",
        "call_id": request.call_id
    }


@router.get("/active/{business_id}")
async def get_active_calls_for_actions(
    business_id: int,
    db: Session = Depends(get_db)
):
    active = db.query(ActiveCall).filter(
        ActiveCall.business_id == business_id,
        ActiveCall.status == "in_progress"
    ).all()
    
    return [
        {
            "call_sid": a.call_sid,
            "caller_number": a.caller_number,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "status": a.status
        }
        for a in active
    ]


@router.get("/available-technicians/{business_id}")
async def get_available_technicians_for_assignment(
    business_id: int,
    db: Session = Depends(get_db)
):
    techs = technician_matcher.get_available_technicians(db, business_id)
    return {"technicians": techs, "count": len(techs)}


@router.post("/auto-assign/{call_id}")
async def auto_assign_technician(
    call_id: int,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    match = technician_matcher.auto_assign_for_call(
        db,
        call_id=call_id,
        service_type=service_type,
        is_emergency=call.is_emergency or False
    )
    
    if not match:
        return {"success": False, "message": "No available technicians found"}
    
    tech = db.query(Technician).filter(Technician.id == match["id"]).first()
    if tech:
        customer_info = {
            "name": call.customer_name or "Customer",
            "phone": call.customer_phone or call.caller_number,
            "address": call.customer_address or "To be confirmed"
        }
        
        appointment_time = "ASAP"
        if call.appointment_time:
            appointment_time = call.appointment_time.strftime("%A, %B %d at %I:%M %p")
        
        dispatcher.dispatch_technician(
            technician_name=tech.name,
            technician_phone=tech.phone,
            customer_info=customer_info,
            appointment_time=appointment_time,
            service_type=call.service_requested or "Service call",
            is_emergency=call.is_emergency or False
        )
    
    return {
        "success": True,
        "message": f"Auto-assigned to {match['name']}",
        "technician": match
    }
