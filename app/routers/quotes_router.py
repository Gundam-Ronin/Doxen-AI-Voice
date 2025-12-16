"""
Phase 8.2 - Quotes API Router
Endpoints for AI-powered quote generation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.session import get_db
from ..database.models import Business, Customer
from ..core.quote_generator import quote_generator

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


class QuoteRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    service_type: str
    job_details: Optional[Dict[str, Any]] = None
    is_emergency: bool = False
    promo_code: Optional[str] = None


class QuoteResponse(BaseModel):
    quote_id: str
    quote_type: str
    customer_name: str
    service_type: str
    subtotal: float
    tax: float
    discount: float
    total: float
    low_estimate: Optional[float]
    high_estimate: Optional[float]
    valid_until: Optional[str]
    notes: str
    voice_response: str


@router.post("/{business_id}/generate")
async def generate_quote(
    business_id: int,
    request: QuoteRequest,
    db: Session = Depends(get_db)
):
    """Generate an AI-powered quote for a service."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    industry = business.industry or "general"
    
    customer_data = {
        "name": request.customer_name,
        "phone": request.customer_phone,
        "email": request.customer_email
    }
    
    job_details = request.job_details or {}
    job_details["is_emergency"] = request.is_emergency
    if request.promo_code:
        job_details["promo_code"] = request.promo_code
    
    quote = quote_generator.generate_quote(
        industry=industry,
        service_type=request.service_type,
        customer_data=customer_data,
        job_details=job_details
    )
    
    voice_response = quote_generator.format_quote_for_voice(quote)
    
    return {
        "quote_id": quote.quote_id,
        "quote_type": quote.quote_type.value,
        "customer_name": quote.customer_name,
        "service_type": quote.service_type,
        "line_items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
                "is_optional": item.is_optional,
                "notes": item.notes
            }
            for item in quote.line_items
        ],
        "subtotal": quote.subtotal,
        "tax": quote.tax,
        "discount": quote.discount,
        "total": quote.total,
        "low_estimate": quote.low_estimate,
        "high_estimate": quote.high_estimate,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "notes": quote.notes,
        "terms": quote.terms,
        "confidence_level": quote.confidence_level,
        "ai_reasoning": quote.ai_reasoning,
        "voice_response": voice_response
    }


@router.get("/{business_id}/price-range")
async def get_price_range(
    business_id: int,
    service_type: str,
    db: Session = Depends(get_db)
):
    """Get price range for a service type."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    industry = business.industry or "general"
    
    price_range = quote_generator.get_price_range(industry, service_type)
    
    if price_range:
        return {
            "service_type": service_type,
            "low": price_range[0],
            "high": price_range[1],
            "industry": industry
        }
    else:
        return {
            "service_type": service_type,
            "message": "Price requires on-site inspection",
            "industry": industry
        }


@router.get("/{business_id}/pricing-catalog")
async def get_pricing_catalog(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get the full pricing catalog for a business's industry."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    industry = business.industry or "general"
    
    pricing = quote_generator.industry_pricing.get(industry.lower(), {})
    
    catalog = []
    for service_key, details in pricing.items():
        catalog.append({
            "service": service_key.replace("_", " ").title(),
            "base_price": details.get("base", 0),
            "low_estimate": details.get("range", [0, 0])[0],
            "high_estimate": details.get("range", [0, 0])[1]
        })
    
    catalog.sort(key=lambda x: x["base_price"])
    
    return {
        "industry": industry,
        "business_name": business.name,
        "services": catalog
    }
