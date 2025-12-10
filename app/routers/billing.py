import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..database.models import Business

router = APIRouter(prefix="/billing", tags=["billing"])

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not STRIPE_WEBHOOK_SECRET:
        return {"status": "webhook secret not configured"}
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    if event_type == "customer.subscription.created":
        await handle_subscription_created(data, db)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(data, db)
    elif event_type == "invoice.paid":
        await handle_invoice_paid(data, db)
    
    return {"status": "success"}

async def handle_subscription_created(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    business = db.query(Business).filter(
        Business.stripe_customer_id == customer_id
    ).first()
    
    if business:
        business.subscription_status = status
        db.commit()

async def handle_subscription_updated(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    business = db.query(Business).filter(
        Business.stripe_customer_id == customer_id
    ).first()
    
    if business:
        business.subscription_status = status
        db.commit()

async def handle_subscription_deleted(subscription: dict, db: Session):
    customer_id = subscription.get("customer")
    
    business = db.query(Business).filter(
        Business.stripe_customer_id == customer_id
    ).first()
    
    if business:
        business.subscription_status = "cancelled"
        db.commit()

async def handle_payment_failed(invoice: dict, db: Session):
    customer_id = invoice.get("customer")
    
    business = db.query(Business).filter(
        Business.stripe_customer_id == customer_id
    ).first()
    
    if business:
        business.subscription_status = "past_due"
        db.commit()

async def handle_invoice_paid(invoice: dict, db: Session):
    customer_id = invoice.get("customer")
    
    business = db.query(Business).filter(
        Business.stripe_customer_id == customer_id
    ).first()
    
    if business and business.subscription_status == "past_due":
        business.subscription_status = "active"
        db.commit()

@router.post("/create-checkout/{business_id}")
async def create_checkout_session(
    business_id: int,
    price_id: str,
    db: Session = Depends(get_db)
):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        if not business.stripe_customer_id:
            customer = stripe.Customer.create(
                name=business.name,
                metadata={"business_id": str(business_id)}
            )
            business.stripe_customer_id = customer.id
            db.commit()
        
        checkout_session = stripe.checkout.Session.create(
            customer=business.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=os.environ.get("BASE_URL", "http://localhost:5000") + "/settings?success=true",
            cancel_url=os.environ.get("BASE_URL", "http://localhost:5000") + "/settings?cancelled=true"
        )
        
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscription/{business_id}")
async def get_subscription_status(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "business_id": business_id,
        "subscription_status": business.subscription_status,
        "stripe_customer_id": business.stripe_customer_id
    }
