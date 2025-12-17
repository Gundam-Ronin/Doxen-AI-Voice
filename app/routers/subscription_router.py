"""
Phase 11 - Subscription & Billing API Router
Stripe SaaS billing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..database.models import Business
from ..core.billing_engine import billing_engine, SubscriptionTier, PRICING_PLANS

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CreateSubscriptionRequest(BaseModel):
    tier: str
    billing_cycle: str = "monthly"
    customer_email: str
    payment_method_id: Optional[str] = None


class UpgradeRequest(BaseModel):
    new_tier: str


@router.get("/plans")
async def get_pricing_plans():
    """Get all available pricing plans."""
    plans = billing_engine.get_pricing_plans()
    return {
        "plans": plans,
        "currency": "USD",
        "annual_discount": "2 months free"
    }


@router.get("/plans/{tier}")
async def get_plan_details(tier: str):
    """Get details for a specific plan."""
    try:
        subscription_tier = SubscriptionTier(tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    plan = PRICING_PLANS.get(subscription_tier)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {
        "tier": tier,
        "name": plan.name,
        "monthly_price": plan.monthly_price / 100,
        "annual_price": plan.annual_price / 100,
        "annual_monthly_price": round(plan.annual_price / 100 / 12, 2),
        "description": plan.description,
        "features": plan.features,
        "limits": plan.limits
    }


@router.post("/{business_id}/subscribe")
async def create_subscription(
    business_id: int,
    request: CreateSubscriptionRequest,
    db: Session = Depends(get_db)
):
    """Create a new subscription for a business."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        tier = SubscriptionTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    result = await billing_engine.create_subscription(
        business_id=business_id,
        tier=tier,
        billing_cycle=request.billing_cycle,
        customer_email=request.customer_email,
        payment_method_id=request.payment_method_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Subscription failed"))
    
    business.stripe_customer_id = result.get("customer_id")
    business.subscription_status = "active"
    db.commit()
    
    return result


@router.post("/{business_id}/upgrade")
async def upgrade_subscription(
    business_id: int,
    request: UpgradeRequest,
    db: Session = Depends(get_db)
):
    """Upgrade or downgrade a subscription."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        new_tier = SubscriptionTier(request.new_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    plan = PRICING_PLANS.get(new_tier)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if not business.subscription_status:
        business.subscription_status = "active"
    
    db.commit()
    
    return {
        "message": "Plan updated successfully",
        "new_tier": new_tier.value,
        "new_price": plan.monthly_price / 100,
        "business_id": business_id
    }


@router.post("/{business_id}/cancel")
async def cancel_subscription(
    business_id: int,
    immediate: bool = False,
    db: Session = Depends(get_db)
):
    """Cancel a subscription."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business.subscription_status = "cancelled" if immediate else "cancelling"
    db.commit()
    
    return {
        "message": "Subscription cancellation scheduled" if not immediate else "Subscription cancelled",
        "immediate": immediate
    }


@router.get("/{business_id}/usage")
async def get_usage_report(
    business_id: int,
    tier_override: str = None,
    db: Session = Depends(get_db)
):
    """Get usage report for a business."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    tier_str = tier_override or business.subscription_status or "starter"
    try:
        tier = SubscriptionTier(tier_str.lower())
    except ValueError:
        tier = SubscriptionTier.STARTER
    
    report = billing_engine.get_usage_report(business_id, tier)
    
    return report


@router.post("/{business_id}/track-usage")
async def track_usage(
    business_id: int,
    metric: str,
    count: int = 1,
    db: Session = Depends(get_db)
):
    """Track usage for a business (internal API)."""
    result = billing_engine.track_usage(business_id, metric, count)
    return result


@router.get("/{business_id}/check-limit")
async def check_usage_limit(
    business_id: int,
    metric: str,
    db: Session = Depends(get_db)
):
    """Check if a usage limit has been reached."""
    tier = SubscriptionTier.STARTER
    
    result = billing_engine.check_usage_limit(business_id, tier, metric)
    return result


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    result = await billing_engine.handle_webhook(payload, sig_header)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/roi-calculator")
async def roi_calculator(
    current_missed_calls: int = 20,
    avg_ticket: float = 350,
    conversion_rate: float = 0.25
):
    """Calculate ROI for potential customers."""
    captured_revenue = current_missed_calls * avg_ticket * conversion_rate
    
    starter_cost = 397
    pro_cost = 697
    elite_cost = 1297
    enterprise_cost = 3500
    
    def calc_roi(cost):
        return ((captured_revenue - cost) / cost) * 100 if cost else 0
    
    return {
        "inputs": {
            "missed_calls_per_month": current_missed_calls,
            "average_ticket": avg_ticket,
            "conversion_rate": conversion_rate
        },
        "potential_revenue": round(captured_revenue, 2),
        "roi_by_plan": {
            "starter": {
                "cost": starter_cost,
                "net_gain": round(captured_revenue - starter_cost, 2),
                "roi_percent": round(calc_roi(starter_cost), 1)
            },
            "pro": {
                "cost": pro_cost,
                "net_gain": round(captured_revenue - pro_cost, 2),
                "roi_percent": round(calc_roi(pro_cost), 1)
            },
            "elite": {
                "cost": elite_cost,
                "net_gain": round(captured_revenue - elite_cost, 2),
                "roi_percent": round(calc_roi(elite_cost), 1)
            },
            "enterprise": {
                "cost": enterprise_cost,
                "net_gain": round(captured_revenue - enterprise_cost, 2),
                "roi_percent": round(calc_roi(enterprise_cost), 1)
            }
        },
        "value_props": [
            "Replace $4,000/month receptionist",
            "20-35% conversion increase",
            "Zero missed calls",
            "Automated follow-ups",
            "Instant AI quotes"
        ]
    }
