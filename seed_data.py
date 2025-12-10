import os
import sys

os.environ.setdefault("DATABASE_URL", os.environ.get("DATABASE_URL", ""))

from app.database.session import SessionLocal, init_db
from app.database.models import Business, Technician, KnowledgebaseDocument

def seed_database():
    init_db()
    db = SessionLocal()
    
    try:
        existing = db.query(Business).first()
        if existing:
            print("Database already seeded")
            return
        
        business = Business(
            owner_id="demo_user",
            name="Premier Plumbing & HVAC",
            phone_number="+15551234567",
            location="Austin, TX Metro Area",
            hours={
                "monday": {"open": "08:00", "close": "18:00"},
                "tuesday": {"open": "08:00", "close": "18:00"},
                "wednesday": {"open": "08:00", "close": "18:00"},
                "thursday": {"open": "08:00", "close": "18:00"},
                "friday": {"open": "08:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "14:00"},
                "sunday": None
            },
            services=[
                "Plumbing Repairs",
                "Drain Cleaning",
                "Water Heater Installation",
                "HVAC Repair",
                "AC Installation",
                "Heating System Maintenance",
                "Emergency Services"
            ],
            pricing={
                "service_call": 89,
                "hourly_rate": 125,
                "emergency_surcharge": 50
            },
            ai_personality="You are friendly, professional, and empathetic. Always prioritize customer comfort and safety. Mention our 24/7 emergency service availability. Offer a 10% discount to first-time customers.",
            subscription_status="active"
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        
        technicians = [
            Technician(
                business_id=business.id,
                name="Mike Johnson",
                phone="+15559876543",
                role="senior_technician",
                skills=["Plumbing", "Water Heaters", "Emergency Repairs"],
                is_available=True
            ),
            Technician(
                business_id=business.id,
                name="Sarah Williams",
                phone="+15554567890",
                role="technician",
                skills=["HVAC", "AC Installation", "Heating"],
                is_available=True
            ),
            Technician(
                business_id=business.id,
                name="Carlos Rodriguez",
                phone="+15552345678",
                role="technician",
                skills=["Plumbing", "Drain Cleaning", "General Repairs"],
                is_available=True
            )
        ]
        
        for tech in technicians:
            db.add(tech)
        db.commit()
        
        kb_docs = [
            KnowledgebaseDocument(
                business_id=business.id,
                title="Service Pricing",
                content="""Our pricing structure:
- Service Call Fee: $89 (waived if you proceed with repairs)
- Hourly Labor Rate: $125/hour
- Emergency Surcharge: $50 (for after-hours calls)
- First-time Customer Discount: 10% off labor

We provide free estimates for major installations. Payment accepted: Credit cards, checks, and financing available for purchases over $500.""",
                category="Pricing"
            ),
            KnowledgebaseDocument(
                business_id=business.id,
                title="Emergency Services",
                content="""We offer 24/7 emergency services for:
- Burst pipes and major water leaks
- No heat during cold weather
- Gas line issues (gas smell)
- Flooding or sewage backup
- No AC during extreme heat

For emergencies, we dispatch technicians within 1 hour. Emergency surcharge of $50 applies to after-hours calls (before 8 AM or after 6 PM).""",
                category="Services"
            ),
            KnowledgebaseDocument(
                business_id=business.id,
                title="Service Areas",
                content="""We proudly serve the greater Austin, TX metropolitan area including:
- Austin
- Round Rock
- Cedar Park
- Georgetown
- Pflugerville
- Leander
- Kyle
- Buda

Travel within 30 miles of downtown Austin is included. Additional mileage charges may apply for distant locations.""",
                category="Coverage"
            ),
            KnowledgebaseDocument(
                business_id=business.id,
                title="Appointment Scheduling",
                content="""We offer flexible appointment windows:
- Morning: 8 AM - 12 PM
- Afternoon: 12 PM - 4 PM  
- Evening: 4 PM - 6 PM (weekdays only)

Same-day service is often available for urgent repairs. We offer 2-hour arrival windows and will call 30 minutes before arrival.

To schedule: We need your name, phone number, address, and a brief description of the issue.""",
                category="Booking"
            )
        ]
        
        for doc in kb_docs:
            db.add(doc)
        db.commit()
        
        print("Database seeded successfully!")
        print(f"Created business: {business.name}")
        print(f"Created {len(technicians)} technicians")
        print(f"Created {len(kb_docs)} knowledge base documents")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
