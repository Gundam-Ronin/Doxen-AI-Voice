"""
Phase 11 - Stripe SaaS Billing Engine
Enterprise-grade subscription and usage management.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os

try:
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
except ImportError:
    stripe = None


class SubscriptionTier(Enum):
    STARTER = "starter"
    PRO = "pro"
    ELITE = "elite"
    ENTERPRISE = "enterprise"


@dataclass
class PricingPlan:
    tier: SubscriptionTier
    name: str
    monthly_price: int
    annual_price: int
    description: str
    features: List[str]
    limits: Dict[str, int]
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_annual: Optional[str] = None


PRICING_PLANS = {
    SubscriptionTier.STARTER: PricingPlan(
        tier=SubscriptionTier.STARTER,
        name="Starter",
        monthly_price=39700,
        annual_price=397000,
        description="AI Answering + Scheduling - Perfect for single-location businesses",
        features=[
            "AI Call Answering (24/7)",
            "Smart Appointment Scheduling",
            "Google Calendar Integration",
            "SMS Confirmations",
            "Basic Analytics Dashboard",
            "1 Phone Number",
            "Email Support"
        ],
        limits={
            "monthly_minutes": 500,
            "monthly_calls": 200,
            "monthly_appointments": 100,
            "locations": 1,
            "technicians": 5,
            "knowledgebase_docs": 50
        }
    ),
    SubscriptionTier.PRO: PricingPlan(
        tier=SubscriptionTier.PRO,
        name="Pro",
        monthly_price=69700,
        annual_price=697000,
        description="Full AI Suite - Outbound calling, quotes, and advanced analytics",
        features=[
            "Everything in Starter",
            "Outbound AI Calling",
            "AI Quote Generation",
            "Lead Scoring & Prioritization",
            "Advanced Analytics & Insights",
            "Technician Performance Tracking",
            "Custom AI Personality",
            "Priority Support",
            "3 Phone Numbers"
        ],
        limits={
            "monthly_minutes": 2000,
            "monthly_calls": 1000,
            "monthly_appointments": 500,
            "monthly_outbound_calls": 500,
            "monthly_quotes": 250,
            "locations": 3,
            "technicians": 15,
            "knowledgebase_docs": 200
        }
    ),
    SubscriptionTier.ELITE: PricingPlan(
        tier=SubscriptionTier.ELITE,
        name="Elite",
        monthly_price=129700,
        annual_price=1297000,
        description="Multi-Location Power - White-label ready with unlimited scale",
        features=[
            "Everything in Pro",
            "White-Label Branding",
            "Multi-Location Support",
            "Custom Voice Cloning",
            "API Access",
            "Dedicated Account Manager",
            "Custom Integrations",
            "SLA Guarantee (99.9%)",
            "10 Phone Numbers",
            "Unlimited Technicians"
        ],
        limits={
            "monthly_minutes": 10000,
            "monthly_calls": 5000,
            "monthly_appointments": 2500,
            "monthly_outbound_calls": 2500,
            "monthly_quotes": 1000,
            "locations": 10,
            "technicians": -1,
            "knowledgebase_docs": 1000
        }
    ),
    SubscriptionTier.ENTERPRISE: PricingPlan(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        monthly_price=350000,
        annual_price=3500000,
        description="Franchise & Enterprise - Unlimited everything with premium support",
        features=[
            "Everything in Elite",
            "Unlimited Locations",
            "Unlimited Minutes",
            "Unlimited Calls",
            "Custom AI Training",
            "On-Premise Option",
            "24/7 Phone Support",
            "Custom SLA",
            "Dedicated Infrastructure",
            "Priority Feature Requests",
            "Quarterly Business Reviews"
        ],
        limits={
            "monthly_minutes": -1,
            "monthly_calls": -1,
            "monthly_appointments": -1,
            "monthly_outbound_calls": -1,
            "monthly_quotes": -1,
            "locations": -1,
            "technicians": -1,
            "knowledgebase_docs": -1
        }
    )
}


@dataclass
class UsageRecord:
    business_id: int
    metric: str
    count: int
    period_start: datetime
    period_end: datetime


@dataclass 
class SubscriptionStatus:
    tier: SubscriptionTier
    status: str
    current_period_start: datetime
    current_period_end: datetime
    usage: Dict[str, int]
    limits: Dict[str, int]
    overage_charges: float = 0.0


class BillingEngine:
    """Enterprise-grade billing and subscription management."""
    
    def __init__(self):
        self.usage_cache: Dict[int, Dict[str, int]] = {}
        self.overage_rates = {
            "monthly_minutes": 0.05,
            "monthly_calls": 0.25,
            "monthly_appointments": 1.00,
            "monthly_outbound_calls": 0.50,
            "monthly_quotes": 0.75
        }
    
    def get_pricing_plans(self) -> List[Dict[str, Any]]:
        """Get all pricing plans for display."""
        plans = []
        for tier, plan in PRICING_PLANS.items():
            plans.append({
                "tier": tier.value,
                "name": plan.name,
                "monthly_price": plan.monthly_price / 100,
                "annual_price": plan.annual_price / 100,
                "annual_monthly_price": round(plan.annual_price / 100 / 12, 2),
                "annual_savings": round((plan.monthly_price * 12 - plan.annual_price) / 100, 2),
                "description": plan.description,
                "features": plan.features,
                "limits": plan.limits
            })
        return plans
    
    def get_plan(self, tier: SubscriptionTier) -> PricingPlan:
        """Get a specific pricing plan."""
        return PRICING_PLANS.get(tier)
    
    async def create_subscription(
        self,
        business_id: int,
        tier: SubscriptionTier,
        billing_cycle: str = "monthly",
        customer_email: str = None,
        payment_method_id: str = None
    ) -> Dict[str, Any]:
        """Create a new subscription in Stripe."""
        if not stripe:
            return {"error": "Stripe not configured", "success": False}
        
        plan = PRICING_PLANS.get(tier)
        if not plan:
            return {"error": "Invalid plan", "success": False}
        
        try:
            customer = stripe.Customer.create(
                email=customer_email,
                metadata={"business_id": str(business_id)}
            )
            
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id
                )
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={"default_payment_method": payment_method_id}
                )
            
            price_id = plan.stripe_price_id_annual if billing_cycle == "annual" else plan.stripe_price_id_monthly
            
            if not price_id:
                price = stripe.Price.create(
                    unit_amount=plan.annual_price if billing_cycle == "annual" else plan.monthly_price,
                    currency="usd",
                    recurring={"interval": "year" if billing_cycle == "annual" else "month"},
                    product_data={
                        "name": f"Doxen AI - {plan.name}",
                        "metadata": {"tier": tier.value}
                    }
                )
                price_id = price.id
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}],
                metadata={"business_id": str(business_id), "tier": tier.value},
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"]
            )
            
            return {
                "success": True,
                "subscription_id": subscription.id,
                "customer_id": customer.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
                "status": subscription.status
            }
            
        except stripe.error.StripeError as e:
            return {"error": str(e), "success": False}
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False
    ) -> Dict[str, Any]:
        """Cancel a subscription."""
        if not stripe:
            return {"error": "Stripe not configured", "success": False}
        
        try:
            if cancel_immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            return {
                "success": True,
                "status": subscription.status,
                "cancel_at": subscription.cancel_at
            }
            
        except stripe.error.StripeError as e:
            return {"error": str(e), "success": False}
    
    async def upgrade_subscription(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier
    ) -> Dict[str, Any]:
        """Upgrade or downgrade a subscription."""
        if not stripe:
            return {"error": "Stripe not configured", "success": False}
        
        plan = PRICING_PLANS.get(new_tier)
        if not plan:
            return {"error": "Invalid plan", "success": False}
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            price = stripe.Price.create(
                unit_amount=plan.monthly_price,
                currency="usd",
                recurring={"interval": "month"},
                product_data={
                    "name": f"Doxen AI - {plan.name}",
                    "metadata": {"tier": new_tier.value}
                }
            )
            
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0].id,
                    "price": price.id
                }],
                proration_behavior="create_prorations",
                metadata={"tier": new_tier.value}
            )
            
            return {
                "success": True,
                "subscription_id": updated.id,
                "new_tier": new_tier.value,
                "status": updated.status
            }
            
        except stripe.error.StripeError as e:
            return {"error": str(e), "success": False}
    
    def track_usage(
        self,
        business_id: int,
        metric: str,
        count: int = 1
    ) -> Dict[str, Any]:
        """Track usage for a business."""
        if business_id not in self.usage_cache:
            self.usage_cache[business_id] = {}
        
        current = self.usage_cache[business_id].get(metric, 0)
        self.usage_cache[business_id][metric] = current + count
        
        return {
            "business_id": business_id,
            "metric": metric,
            "current_usage": self.usage_cache[business_id][metric]
        }
    
    def check_usage_limit(
        self,
        business_id: int,
        tier: SubscriptionTier,
        metric: str
    ) -> Dict[str, Any]:
        """Check if a business has exceeded usage limits."""
        plan = PRICING_PLANS.get(tier)
        if not plan:
            return {"allowed": False, "error": "Invalid plan"}
        
        limit = plan.limits.get(metric, 0)
        if limit == -1:
            return {"allowed": True, "unlimited": True}
        
        current = self.usage_cache.get(business_id, {}).get(metric, 0)
        
        is_over = current >= limit
        is_soft_limit = current >= limit * 0.9
        
        return {
            "allowed": not is_over,
            "current": current,
            "limit": limit,
            "percentage": round(current / limit * 100, 1) if limit > 0 else 0,
            "soft_limit_warning": is_soft_limit and not is_over,
            "hard_limit_reached": is_over
        }
    
    def calculate_overage(
        self,
        business_id: int,
        tier: SubscriptionTier
    ) -> Dict[str, Any]:
        """Calculate overage charges for a business."""
        plan = PRICING_PLANS.get(tier)
        if not plan:
            return {"error": "Invalid plan"}
        
        usage = self.usage_cache.get(business_id, {})
        overages = {}
        total_overage = 0.0
        
        for metric, limit in plan.limits.items():
            if limit == -1:
                continue
            
            current = usage.get(metric, 0)
            if current > limit:
                over_amount = current - limit
                rate = self.overage_rates.get(metric, 0.10)
                charge = over_amount * rate
                overages[metric] = {
                    "over_by": over_amount,
                    "rate": rate,
                    "charge": round(charge, 2)
                }
                total_overage += charge
        
        return {
            "business_id": business_id,
            "overages": overages,
            "total_overage": round(total_overage, 2)
        }
    
    def get_usage_report(
        self,
        business_id: int,
        tier: SubscriptionTier
    ) -> Dict[str, Any]:
        """Get a complete usage report for a business."""
        plan = PRICING_PLANS.get(tier)
        if not plan:
            return {"error": "Invalid plan"}
        
        usage = self.usage_cache.get(business_id, {})
        
        report = {
            "business_id": business_id,
            "tier": tier.value,
            "plan_name": plan.name,
            "metrics": {}
        }
        
        for metric, limit in plan.limits.items():
            current = usage.get(metric, 0)
            if limit == -1:
                report["metrics"][metric] = {
                    "current": current,
                    "limit": "Unlimited",
                    "percentage": 0,
                    "status": "good"
                }
            else:
                pct = round(current / limit * 100, 1) if limit > 0 else 0
                status = "good" if pct < 80 else "warning" if pct < 100 else "exceeded"
                report["metrics"][metric] = {
                    "current": current,
                    "limit": limit,
                    "percentage": pct,
                    "status": status
                }
        
        return report
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        if not stripe:
            return {"error": "Stripe not configured"}
        
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return {"error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"error": "Invalid signature"}
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        if event_type == "invoice.payment_succeeded":
            return {
                "action": "payment_success",
                "customer_id": data["customer"],
                "amount": data["amount_paid"]
            }
        
        elif event_type == "invoice.payment_failed":
            return {
                "action": "payment_failed",
                "customer_id": data["customer"],
                "attempt_count": data.get("attempt_count", 1)
            }
        
        elif event_type == "customer.subscription.deleted":
            return {
                "action": "subscription_cancelled",
                "subscription_id": data["id"],
                "customer_id": data["customer"]
            }
        
        elif event_type == "customer.subscription.updated":
            return {
                "action": "subscription_updated",
                "subscription_id": data["id"],
                "status": data["status"]
            }
        
        return {"action": "unhandled", "event_type": event_type}


billing_engine = BillingEngine()
