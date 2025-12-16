"""
Phase 9 - Analytics API Router
Endpoints for business analytics and insights.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from ..database.session import get_db
from ..database.models import Business, Call, Appointment, Technician, CallLog
from ..core.analytics_engine import analytics_engine
from ..core.lead_scoring import lead_scoring_engine

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/{business_id}/dashboard")
async def get_dashboard(
    business_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get complete analytics dashboard."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    start_date = datetime.now() - timedelta(days=days)
    
    calls = db.query(Call).filter(
        Call.business_id == business_id,
        Call.start_time >= start_date
    ).all()
    
    appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.created_at >= start_date
    ).all()
    
    technicians = db.query(Technician).filter(
        Technician.business_id == business_id
    ).all()
    
    calls_data = [
        {
            "id": c.id,
            "start_time": c.start_time.isoformat() if c.start_time else None,
            "duration_seconds": c.duration_seconds or 0,
            "outcome": c.outcome or "unknown",
            "service_type": (c.extracted_fields or {}).get("service_type", "general")
        }
        for c in calls
    ]
    
    appointments_data = [
        {
            "id": a.id,
            "technician_id": a.technician_id,
            "status": a.status or "unknown",
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "total_price": (a.extra_data or {}).get("price", 0),
            "rating": (a.extra_data or {}).get("rating"),
            "was_on_time": (a.extra_data or {}).get("was_on_time", True),
            "required_callback": (a.extra_data or {}).get("callback", False),
            "actual_duration": a.duration_minutes or 60
        }
        for a in appointments
    ]
    
    technicians_data = [
        {
            "id": t.id,
            "name": t.name,
            "skills": t.skills
        }
        for t in technicians
    ]
    
    dashboard = analytics_engine.get_dashboard_summary(
        business_id,
        calls=calls_data,
        appointments=appointments_data,
        technicians=technicians_data
    )
    
    return dashboard


@router.get("/{business_id}/metrics")
async def get_metrics(
    business_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get performance metrics for a date range."""
    try:
        start = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=30)
        end = datetime.fromisoformat(end_date) if end_date else datetime.now()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    calls = db.query(Call).filter(
        Call.business_id == business_id,
        Call.start_time >= start,
        Call.start_time <= end
    ).all()
    
    appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.created_at >= start,
        Appointment.created_at <= end
    ).all()
    
    calls_data = [
        {
            "duration_seconds": c.duration_seconds,
            "outcome": c.outcome
        }
        for c in calls
    ]
    
    appointments_data = [
        {
            "status": a.status,
            "total_price": a.extra_data.get("price", 0) if a.extra_data else 0
        }
        for a in appointments
    ]
    
    metrics = analytics_engine.get_performance_metrics(
        business_id,
        start_date=start,
        end_date=end,
        calls=calls_data,
        appointments=appointments_data
    )
    
    return {
        "total_calls": metrics.total_calls,
        "answered_calls": metrics.answered_calls,
        "missed_calls": metrics.missed_calls,
        "avg_call_duration": metrics.avg_call_duration,
        "conversion_rate": metrics.conversion_rate,
        "appointments_booked": metrics.appointments_booked,
        "appointments_completed": metrics.appointments_completed,
        "revenue": metrics.revenue,
        "avg_ticket": metrics.avg_ticket,
        "customer_satisfaction": metrics.customer_satisfaction,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        }
    }


@router.get("/{business_id}/technicians")
async def get_technician_analytics(
    business_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get technician performance analytics."""
    start_date = datetime.now() - timedelta(days=days)
    
    technicians = db.query(Technician).filter(
        Technician.business_id == business_id
    ).all()
    
    appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.created_at >= start_date
    ).all()
    
    technicians_data = [
        {"id": t.id, "name": t.name}
        for t in technicians
    ]
    
    appointments_data = [
        {
            "technician_id": a.technician_id,
            "status": a.status or "unknown",
            "total_price": (a.extra_data or {}).get("price", 0),
            "rating": (a.extra_data or {}).get("rating"),
            "was_on_time": (a.extra_data or {}).get("was_on_time", True),
            "required_callback": (a.extra_data or {}).get("callback", False),
            "actual_duration": a.duration_minutes or 60
        }
        for a in appointments
    ]
    
    performance = analytics_engine.get_technician_performance(
        technicians_data,
        appointments_data
    )
    
    return {
        "technicians": [
            {
                "id": p.technician_id,
                "name": p.technician_name,
                "jobs_completed": p.jobs_completed,
                "revenue_generated": p.revenue_generated,
                "avg_rating": p.avg_rating,
                "on_time_rate": p.on_time_rate,
                "callback_rate": p.callback_rate,
                "avg_job_duration": p.avg_job_duration
            }
            for p in performance
        ],
        "period_days": days
    }


@router.get("/{business_id}/call-patterns")
async def get_call_patterns(
    business_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Analyze call patterns."""
    start_date = datetime.now() - timedelta(days=days)
    
    calls = db.query(Call).filter(
        Call.business_id == business_id,
        Call.start_time >= start_date
    ).all()
    
    calls_data = [
        {
            "start_time": c.start_time.isoformat() if c.start_time else None,
            "outcome": c.outcome or "unknown",
            "service_type": (c.extracted_fields or {}).get("service_type", "general")
        }
        for c in calls
    ]
    
    patterns = analytics_engine.analyze_call_patterns(calls_data)
    
    return patterns


@router.get("/{business_id}/lead-scores")
async def get_lead_scores(
    business_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get lead scores for recent calls."""
    calls = db.query(Call).filter(
        Call.business_id == business_id
    ).order_by(Call.start_time.desc()).limit(limit).all()
    
    scored_leads = []
    for call in calls:
        customer_data = {
            "name": call.extracted_fields.get("name") if call.extracted_fields else None,
            "phone_number": call.caller_phone,
            "address": call.extracted_fields.get("address") if call.extracted_fields else None,
            "zip_code": call.extracted_fields.get("zip_code") if call.extracted_fields else None
        }
        
        call_data = {
            "service_type": call.extracted_fields.get("service_type") if call.extracted_fields else "",
            "urgency": "emergency" if call.is_emergency else "normal",
            "is_emergency": call.is_emergency,
            "duration_seconds": call.duration_seconds or 0,
            "call_time": call.start_time.isoformat() if call.start_time else None
        }
        
        score = lead_scoring_engine.score_lead(customer_data, call_data)
        
        scored_leads.append({
            "call_id": call.id,
            "caller_phone": call.caller_phone,
            "customer_name": customer_data.get("name"),
            "score": score.total_score,
            "tier": score.tier.value,
            "conversion_probability": score.conversion_probability,
            "estimated_value": score.estimated_value,
            "priority_rank": score.priority_rank,
            "recommendations": score.recommendations[:3]
        })
    
    scored_leads.sort(key=lambda x: x["priority_rank"])
    
    return {"leads": scored_leads}


@router.get("/{business_id}/predictions")
async def get_predictions(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get predictive analytics."""
    historical = []
    for month_offset in range(6):
        start = datetime.now() - timedelta(days=30 * (month_offset + 1))
        end = datetime.now() - timedelta(days=30 * month_offset)
        
        appointments = db.query(Appointment).filter(
            Appointment.business_id == business_id,
            Appointment.created_at >= start,
            Appointment.created_at <= end,
            Appointment.status == "completed"
        ).all()
        
        revenue = sum(
            a.extra_data.get("price", 0) if a.extra_data else 0
            for a in appointments
        )
        
        historical.append({
            "month": start.strftime("%B %Y"),
            "revenue": revenue
        })
    
    current_calls = db.query(Call).filter(
        Call.business_id == business_id,
        Call.start_time >= datetime.now() - timedelta(days=30)
    ).all()
    
    current_appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.created_at >= datetime.now() - timedelta(days=30)
    ).all()
    
    calls_data = [{"duration_seconds": c.duration_seconds, "outcome": c.outcome} for c in current_calls]
    appointments_data = [
        {"status": a.status, "total_price": a.extra_data.get("price", 0) if a.extra_data else 0}
        for a in current_appointments
    ]
    
    current_metrics = analytics_engine.get_performance_metrics(
        business_id,
        calls=calls_data,
        appointments=appointments_data
    )
    
    predictions = analytics_engine.generate_predictions(historical, current_metrics)
    
    return {
        "predictions": [
            {
                "metric": p.metric,
                "current_value": p.current_value,
                "predicted_value": p.predicted_value,
                "confidence": p.confidence,
                "trend": p.trend,
                "factors": p.factors,
                "recommendations": p.recommendations
            }
            for p in predictions
        ]
    }
