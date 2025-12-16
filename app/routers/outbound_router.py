"""
Phase 8.1 - Outbound Calling API Router
Endpoints for managing outbound AI calls.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.session import get_db
from ..database.models import Business, Customer, Call
from ..core.outbound_calling import outbound_calling_engine, OutboundCallRequest, OutboundCallType

router = APIRouter(prefix="/api/outbound", tags=["outbound"])


class ScheduleCallRequest(BaseModel):
    customer_phone: str
    customer_name: str
    call_type: str
    context: Optional[dict] = None
    scheduled_time: Optional[str] = None
    priority: int = 5


class OutboundCallResponse(BaseModel):
    success: bool
    message: str
    call_sid: Optional[str] = None


@router.post("/{business_id}/schedule")
async def schedule_outbound_call(
    business_id: int,
    request: ScheduleCallRequest,
    db: Session = Depends(get_db)
):
    """Schedule an outbound call."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        call_type = OutboundCallType(request.call_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid call type. Valid types: {[t.value for t in OutboundCallType]}"
        )
    
    scheduled = None
    if request.scheduled_time:
        try:
            scheduled = datetime.fromisoformat(request.scheduled_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_time format")
    
    call_request = OutboundCallRequest(
        call_type=call_type,
        customer_phone=request.customer_phone,
        customer_name=request.customer_name,
        business_id=business_id,
        business_name=business.name,
        context=request.context or {},
        scheduled_time=scheduled,
        priority=request.priority
    )
    
    success = outbound_calling_engine.queue_call(call_request)
    
    return {
        "success": success,
        "message": f"Call scheduled for {call_request.scheduled_time.strftime('%I:%M %p') if call_request.scheduled_time else 'immediately'}",
        "call_type": call_type.value,
        "queue_position": len(outbound_calling_engine.call_queue)
    }


@router.post("/{business_id}/missed-call-followup")
async def schedule_missed_call_followup(
    business_id: int,
    customer_phone: str,
    customer_name: str = "Customer",
    delay_minutes: int = 30,
    db: Session = Depends(get_db)
):
    """Schedule a follow-up call for a missed call."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    success = outbound_calling_engine.schedule_missed_call_followup(
        customer_phone=customer_phone,
        customer_name=customer_name,
        business_id=business_id,
        business_name=business.name,
        delay_minutes=delay_minutes
    )
    
    return {
        "success": success,
        "message": f"Missed call follow-up scheduled in {delay_minutes} minutes"
    }


@router.post("/{business_id}/review-request")
async def schedule_review_request(
    business_id: int,
    customer_phone: str,
    customer_name: str,
    technician_name: str,
    delay_hours: int = 2,
    db: Session = Depends(get_db)
):
    """Schedule a review request call after service completion."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    success = outbound_calling_engine.schedule_review_request(
        customer_phone=customer_phone,
        customer_name=customer_name,
        business_id=business_id,
        business_name=business.name,
        technician_name=technician_name,
        delay_hours=delay_hours
    )
    
    return {
        "success": success,
        "message": f"Review request scheduled in {delay_hours} hours"
    }


@router.get("/{business_id}/queue")
async def get_call_queue(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get the current outbound call queue."""
    queue = []
    for call in outbound_calling_engine.call_queue:
        if call.business_id == business_id:
            queue.append({
                "customer_phone": call.customer_phone,
                "customer_name": call.customer_name,
                "call_type": call.call_type.value if hasattr(call.call_type, 'value') else str(call.call_type),
                "scheduled_time": call.scheduled_time.isoformat() if call.scheduled_time else None,
                "priority": call.priority
            })
    
    return {
        "business_id": business_id,
        "queue": queue,
        "total": len(queue)
    }


@router.post("/{business_id}/process-queue")
async def process_call_queue(
    business_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Process pending outbound calls in the queue."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    base_url = str(request.base_url).rstrip("/")
    
    results = outbound_calling_engine.process_queue(base_url)
    
    return {
        "processed": len(results),
        "results": [
            {
                "success": r.success,
                "status": r.status,
                "message": r.message,
                "call_sid": r.call_sid
            }
            for r in results
        ]
    }


@router.get("/call-types")
async def get_call_types():
    """Get available outbound call types."""
    return {
        "call_types": [
            {"value": t.value, "name": t.name.replace("_", " ").title()}
            for t in OutboundCallType
        ]
    }
