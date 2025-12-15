"""
Universal Business Router - Multi-tenant business management and onboarding.
Supports any home service industry with dynamic configuration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.database.session import get_db
from app.database.models import (
    Business, ServiceCategory, Technician, Customer,
    BusinessSetting, KnowledgebaseDocument
)

router = APIRouter(prefix="/api/business", tags=["business"])


class ServiceCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sub_services: List[str] = []
    required_fields: List[str] = ["name", "phone", "address"]
    default_duration_minutes: int = 60
    allow_urgent: bool = True
    extra_data: Dict[str, Any] = {}


class TechnicianCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    role: str = "technician"
    skills: List[str] = []
    home_zip: Optional[str] = None
    service_radius_miles: int = 25
    availability: Dict[str, List[str]] = {}


class BusinessCreate(BaseModel):
    name: str
    owner_id: str
    industry: str = "general"
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    coverage_area: List[str] = []
    business_hours: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "monday": ["09:00-17:00"],
            "tuesday": ["09:00-17:00"],
            "wednesday": ["09:00-17:00"],
            "thursday": ["09:00-17:00"],
            "friday": ["09:00-17:00"]
        }
    )
    dispatch_rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "mode": "skill_based",
            "max_distance_miles": 25,
            "auto_dispatch_enabled": True
        }
    )
    pricing_rules: Dict[str, Any] = {}
    custom_fields: List[Dict[str, Any]] = []
    technician_types: List[Dict[str, Any]] = []
    ai_personality: str = "friendly and professional"


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    coverage_area: Optional[List[str]] = None
    business_hours: Optional[Dict[str, List[str]]] = None
    dispatch_rules: Optional[Dict[str, Any]] = None
    pricing_rules: Optional[Dict[str, Any]] = None
    custom_fields: Optional[List[Dict[str, Any]]] = None
    technician_types: Optional[List[Dict[str, Any]]] = None
    ai_personality: Optional[str] = None
    calendar_integration: Optional[Dict[str, Any]] = None


class BusinessSettingUpdate(BaseModel):
    setting_key: str
    setting_value: Any


class OnboardingRequest(BaseModel):
    name: str
    owner_id: str
    industry: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    coverage_area: List[str] = []
    business_hours: Dict[str, List[str]] = {}
    service_categories: List[ServiceCategoryCreate] = []
    technicians: List[TechnicianCreate] = []
    pricing_rules: Dict[str, Any] = {}
    custom_fields: List[Dict[str, Any]] = []
    dispatch_mode: str = "skill_based"
    ai_personality: str = "friendly and professional"


INDUSTRY_TEMPLATES = {
    "hvac": {
        "service_categories": [
            {"name": "AC Repair", "sub_services": ["Coolant Recharge", "Compressor Repair", "Fan Motor"], "default_duration_minutes": 90},
            {"name": "Heating Repair", "sub_services": ["Furnace Repair", "Heat Pump", "Thermostat"], "default_duration_minutes": 90},
            {"name": "AC Installation", "sub_services": ["Central AC", "Mini Split", "Window Unit"], "default_duration_minutes": 240},
            {"name": "Maintenance", "sub_services": ["Tune-Up", "Filter Replacement", "Duct Cleaning"], "default_duration_minutes": 60}
        ],
        "custom_fields": [
            {"field_name": "System Type", "type": "enum", "options": ["Central AC", "Heat Pump", "Furnace", "Mini Split"]},
            {"field_name": "Unit Age", "type": "string"},
            {"field_name": "Brand", "type": "string"}
        ],
        "technician_types": [
            {"role": "HVAC Technician", "skills": ["AC Repair", "Heating Repair", "Installation", "Maintenance"]}
        ]
    },
    "plumbing": {
        "service_categories": [
            {"name": "Drain Cleaning", "sub_services": ["Kitchen Drain", "Bathroom Drain", "Main Line"], "default_duration_minutes": 60},
            {"name": "Leak Repair", "sub_services": ["Pipe Repair", "Faucet Repair", "Toilet Repair"], "default_duration_minutes": 60},
            {"name": "Water Heater", "sub_services": ["Repair", "Installation", "Tankless"], "default_duration_minutes": 120},
            {"name": "Emergency", "sub_services": ["Burst Pipe", "Sewer Backup", "No Water"], "default_duration_minutes": 90}
        ],
        "custom_fields": [
            {"field_name": "Issue Location", "type": "string"},
            {"field_name": "Fixture Type", "type": "enum", "options": ["Sink", "Toilet", "Shower", "Tub", "Water Heater", "Pipes"]}
        ],
        "technician_types": [
            {"role": "Plumber", "skills": ["Drain Cleaning", "Leak Repair", "Water Heater", "Emergency"]}
        ]
    },
    "electrical": {
        "service_categories": [
            {"name": "Outlet/Switch Repair", "sub_services": ["Outlet Replacement", "Switch Repair", "GFCI"], "default_duration_minutes": 45},
            {"name": "Panel Services", "sub_services": ["Panel Upgrade", "Breaker Replacement", "Inspection"], "default_duration_minutes": 120},
            {"name": "Lighting", "sub_services": ["Fixture Install", "Ceiling Fan", "Recessed Lighting"], "default_duration_minutes": 60},
            {"name": "Emergency", "sub_services": ["No Power", "Sparking", "Safety Hazard"], "default_duration_minutes": 60}
        ],
        "custom_fields": [
            {"field_name": "Panel Age", "type": "string"},
            {"field_name": "Issue Description", "type": "string"}
        ],
        "technician_types": [
            {"role": "Electrician", "skills": ["Residential", "Commercial", "Emergency"]}
        ]
    },
    "cleaning": {
        "service_categories": [
            {"name": "Regular Cleaning", "sub_services": ["Weekly", "Bi-Weekly", "Monthly"], "default_duration_minutes": 120},
            {"name": "Deep Cleaning", "sub_services": ["Move-In", "Move-Out", "Spring Cleaning"], "default_duration_minutes": 240},
            {"name": "Commercial Cleaning", "sub_services": ["Office", "Retail", "Medical"], "default_duration_minutes": 180}
        ],
        "custom_fields": [
            {"field_name": "Home Type", "type": "enum", "options": ["House", "Apartment", "Condo", "Office"]},
            {"field_name": "Bedrooms", "type": "number"},
            {"field_name": "Bathrooms", "type": "number"},
            {"field_name": "Square Footage", "type": "number"},
            {"field_name": "Pets", "type": "boolean"}
        ],
        "technician_types": [
            {"role": "Cleaning Team", "skills": ["Residential", "Commercial", "Deep Cleaning"]}
        ]
    },
    "pest_control": {
        "service_categories": [
            {"name": "General Pest", "sub_services": ["Ants", "Roaches", "Spiders", "Crickets"], "default_duration_minutes": 45},
            {"name": "Rodent Control", "sub_services": ["Mice", "Rats", "Exclusion"], "default_duration_minutes": 60},
            {"name": "Termite", "sub_services": ["Inspection", "Treatment", "Prevention"], "default_duration_minutes": 120},
            {"name": "Bed Bugs", "sub_services": ["Inspection", "Heat Treatment", "Chemical"], "default_duration_minutes": 180}
        ],
        "custom_fields": [
            {"field_name": "Pest Type", "type": "string"},
            {"field_name": "Severity", "type": "enum", "options": ["Mild", "Moderate", "Severe"]},
            {"field_name": "Previous Treatment", "type": "boolean"}
        ],
        "technician_types": [
            {"role": "Pest Technician", "skills": ["General Pest", "Rodent", "Termite", "Bed Bugs"]}
        ]
    },
    "landscaping": {
        "service_categories": [
            {"name": "Lawn Care", "sub_services": ["Mowing", "Edging", "Fertilization"], "default_duration_minutes": 60},
            {"name": "Tree Service", "sub_services": ["Trimming", "Removal", "Planting"], "default_duration_minutes": 180},
            {"name": "Irrigation", "sub_services": ["Install", "Repair", "Winterize"], "default_duration_minutes": 90},
            {"name": "Hardscape", "sub_services": ["Patio", "Walkway", "Retaining Wall"], "default_duration_minutes": 480}
        ],
        "custom_fields": [
            {"field_name": "Property Size", "type": "string"},
            {"field_name": "Lawn Type", "type": "string"},
            {"field_name": "Service Frequency", "type": "enum", "options": ["Weekly", "Bi-Weekly", "Monthly", "One-Time"]}
        ],
        "technician_types": [
            {"role": "Landscaper", "skills": ["Lawn Care", "Tree Service", "Irrigation", "Hardscape"]}
        ]
    },
    "roofing": {
        "service_categories": [
            {"name": "Roof Repair", "sub_services": ["Leak Repair", "Shingle Repair", "Flashing"], "default_duration_minutes": 180},
            {"name": "Roof Replacement", "sub_services": ["Shingle", "Metal", "Tile", "Flat"], "default_duration_minutes": 480},
            {"name": "Inspection", "sub_services": ["Annual", "Storm Damage", "Pre-Purchase"], "default_duration_minutes": 60},
            {"name": "Gutter", "sub_services": ["Cleaning", "Repair", "Installation"], "default_duration_minutes": 120}
        ],
        "custom_fields": [
            {"field_name": "Roof Age", "type": "string"},
            {"field_name": "Roof Type", "type": "enum", "options": ["Shingle", "Metal", "Tile", "Flat"]},
            {"field_name": "Stories", "type": "number"},
            {"field_name": "Damage Type", "type": "string"}
        ],
        "technician_types": [
            {"role": "Roofer", "skills": ["Repair", "Replacement", "Inspection", "Gutter"]}
        ]
    },
    "general": {
        "service_categories": [
            {"name": "General Service", "sub_services": ["Standard", "Premium"], "default_duration_minutes": 60},
            {"name": "Emergency", "sub_services": ["Urgent Response"], "default_duration_minutes": 60}
        ],
        "custom_fields": [
            {"field_name": "Service Description", "type": "string"}
        ],
        "technician_types": [
            {"role": "Technician", "skills": ["General"]}
        ]
    }
}


@router.post("/onboard")
async def onboard_business(request: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Complete business onboarding in one API call.
    Creates business, service categories, technicians, and default settings.
    """
    try:
        template = INDUSTRY_TEMPLATES.get(request.industry.lower(), INDUSTRY_TEMPLATES["general"])
        
        business = Business(
            business_uuid=str(uuid.uuid4()),
            owner_id=request.owner_id,
            name=request.name,
            industry=request.industry.lower(),
            phone_number=request.phone_number,
            email=request.email,
            address=request.address,
            coverage_area=request.coverage_area,
            business_hours=request.business_hours or {
                "monday": ["09:00-17:00"],
                "tuesday": ["09:00-17:00"],
                "wednesday": ["09:00-17:00"],
                "thursday": ["09:00-17:00"],
                "friday": ["09:00-17:00"]
            },
            hours=request.business_hours,
            dispatch_rules={
                "mode": request.dispatch_mode,
                "max_distance_miles": 25,
                "auto_dispatch_enabled": True
            },
            pricing_rules=request.pricing_rules,
            custom_fields=request.custom_fields or template.get("custom_fields", []),
            technician_types=template.get("technician_types", []),
            ai_personality=request.ai_personality
        )
        db.add(business)
        db.flush()
        
        categories_to_add = request.service_categories or [
            ServiceCategoryCreate(**cat) for cat in template.get("service_categories", [])
        ]
        
        for cat_data in categories_to_add:
            if isinstance(cat_data, dict):
                cat_data = ServiceCategoryCreate(**cat_data)
            
            category = ServiceCategory(
                category_uuid=str(uuid.uuid4()),
                business_id=business.id,
                name=cat_data.name,
                description=cat_data.description,
                sub_services=cat_data.sub_services,
                required_fields=cat_data.required_fields,
                default_duration_minutes=cat_data.default_duration_minutes,
                allow_urgent=cat_data.allow_urgent,
                extra_data=cat_data.extra_data
            )
            db.add(category)
        
        for tech_data in request.technicians:
            technician = Technician(
                technician_uuid=str(uuid.uuid4()),
                business_id=business.id,
                name=tech_data.name,
                phone=tech_data.phone,
                email=tech_data.email,
                role=tech_data.role,
                skills=tech_data.skills,
                home_zip=tech_data.home_zip,
                service_radius_miles=tech_data.service_radius_miles,
                availability=tech_data.availability,
                is_available=True,
                status="active"
            )
            db.add(technician)
        
        default_settings = [
            ("ask_for_email", {"enabled": True}),
            ("allow_emergency", {"enabled": True}),
            ("auto_dispatch", {"enabled": True}),
            ("send_confirmations", {"sms": True, "email": True}),
            ("review_request", {"enabled": True, "delay_hours": 24})
        ]
        
        for key, value in default_settings:
            setting = BusinessSetting(
                business_id=business.id,
                setting_key=key,
                setting_value=value
            )
            db.add(setting)
        
        db.commit()
        db.refresh(business)
        
        return {
            "success": True,
            "business_id": business.id,
            "business_uuid": business.business_uuid,
            "message": f"Successfully onboarded {request.name} as a {request.industry} business",
            "services_created": len(categories_to_add),
            "technicians_created": len(request.technicians)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_businesses(
    owner_id: Optional[str] = None,
    industry: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all businesses, optionally filtered by owner or industry."""
    query = db.query(Business)
    
    if owner_id:
        query = query.filter(Business.owner_id == owner_id)
    if industry:
        query = query.filter(Business.industry == industry.lower())
    
    businesses = query.all()
    
    return [{
        "id": b.id,
        "business_uuid": b.business_uuid,
        "name": b.name,
        "industry": b.industry,
        "phone_number": b.phone_number,
        "email": b.email,
        "subscription_status": b.subscription_status,
        "created_at": b.created_at.isoformat() if b.created_at else None
    } for b in businesses]


@router.get("/{business_id}")
async def get_business(business_id: int, db: Session = Depends(get_db)):
    """Get full business profile."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "id": business.id,
        "business_uuid": business.business_uuid,
        "name": business.name,
        "industry": business.industry,
        "phone_number": business.phone_number,
        "email": business.email,
        "address": business.address,
        "coverage_area": business.coverage_area,
        "business_hours": business.business_hours or business.hours,
        "dispatch_rules": business.dispatch_rules,
        "pricing_rules": business.pricing_rules,
        "custom_fields": business.custom_fields,
        "technician_types": business.technician_types,
        "ai_personality": business.ai_personality,
        "calendar_integration": business.calendar_integration,
        "subscription_status": business.subscription_status,
        "created_at": business.created_at.isoformat() if business.created_at else None,
        "updated_at": business.updated_at.isoformat() if business.updated_at else None
    }


@router.put("/{business_id}")
async def update_business(
    business_id: int,
    update: BusinessUpdate,
    db: Session = Depends(get_db)
):
    """Update business profile."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(business, key, value)
    
    business.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(business)
    
    return {"success": True, "message": "Business updated successfully"}


@router.post("/{business_id}/service-categories")
async def add_service_category(
    business_id: int,
    category: ServiceCategoryCreate,
    db: Session = Depends(get_db)
):
    """Add a service category to a business."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    new_category = ServiceCategory(
        category_uuid=str(uuid.uuid4()),
        business_id=business_id,
        name=category.name,
        description=category.description,
        sub_services=category.sub_services,
        required_fields=category.required_fields,
        default_duration_minutes=category.default_duration_minutes,
        allow_urgent=category.allow_urgent,
        extra_data=category.extra_data
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return {
        "success": True,
        "category_id": new_category.id,
        "category_uuid": new_category.category_uuid
    }


@router.get("/{business_id}/service-categories")
async def list_service_categories(business_id: int, db: Session = Depends(get_db)):
    """List all service categories for a business."""
    categories = db.query(ServiceCategory).filter(ServiceCategory.business_id == business_id).all()
    
    return [{
        "id": cat.id,
        "category_uuid": cat.category_uuid,
        "name": cat.name,
        "description": cat.description,
        "sub_services": cat.sub_services,
        "required_fields": cat.required_fields,
        "default_duration_minutes": cat.default_duration_minutes,
        "allow_urgent": cat.allow_urgent
    } for cat in categories]


@router.post("/{business_id}/technicians")
async def add_technician(
    business_id: int,
    technician: TechnicianCreate,
    db: Session = Depends(get_db)
):
    """Add a technician to a business."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    new_tech = Technician(
        technician_uuid=str(uuid.uuid4()),
        business_id=business_id,
        name=technician.name,
        phone=technician.phone,
        email=technician.email,
        role=technician.role,
        skills=technician.skills,
        home_zip=technician.home_zip,
        service_radius_miles=technician.service_radius_miles,
        availability=technician.availability,
        is_available=True,
        status="active"
    )
    db.add(new_tech)
    db.commit()
    db.refresh(new_tech)
    
    return {
        "success": True,
        "technician_id": new_tech.id,
        "technician_uuid": new_tech.technician_uuid
    }


@router.get("/{business_id}/technicians")
async def list_technicians(
    business_id: int,
    available_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all technicians for a business."""
    query = db.query(Technician).filter(Technician.business_id == business_id)
    
    if available_only:
        query = query.filter(Technician.is_available == True, Technician.status == "active")
    
    technicians = query.all()
    
    return [{
        "id": tech.id,
        "technician_uuid": tech.technician_uuid,
        "name": tech.name,
        "phone": tech.phone,
        "email": tech.email,
        "role": tech.role,
        "skills": tech.skills,
        "home_zip": tech.home_zip,
        "service_radius_miles": tech.service_radius_miles,
        "is_available": tech.is_available,
        "status": tech.status
    } for tech in technicians]


@router.get("/{business_id}/customers")
async def list_customers(
    business_id: int,
    customer_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List customers/leads for a business."""
    query = db.query(Customer).filter(Customer.business_id == business_id)
    
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    
    customers = query.order_by(Customer.created_at.desc()).limit(limit).all()
    
    return [{
        "id": c.id,
        "customer_uuid": c.customer_uuid,
        "name": c.name,
        "phone_number": c.phone_number,
        "email": c.email,
        "address": c.address,
        "customer_type": c.customer_type,
        "lead_score": c.lead_score,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in customers]


@router.get("/{business_id}/settings")
async def get_business_settings(business_id: int, db: Session = Depends(get_db)):
    """Get all settings for a business."""
    settings = db.query(BusinessSetting).filter(BusinessSetting.business_id == business_id).all()
    
    return {s.setting_key: s.setting_value for s in settings}


@router.put("/{business_id}/settings")
async def update_business_setting(
    business_id: int,
    setting: BusinessSettingUpdate,
    db: Session = Depends(get_db)
):
    """Update or create a business setting."""
    existing = db.query(BusinessSetting).filter(
        BusinessSetting.business_id == business_id,
        BusinessSetting.setting_key == setting.setting_key
    ).first()
    
    if existing:
        existing.setting_value = setting.setting_value
        existing.updated_at = datetime.utcnow()
    else:
        new_setting = BusinessSetting(
            business_id=business_id,
            setting_key=setting.setting_key,
            setting_value=setting.setting_value
        )
        db.add(new_setting)
    
    db.commit()
    
    return {"success": True, "message": f"Setting '{setting.setting_key}' updated"}


@router.get("/industries/templates")
async def get_industry_templates():
    """Get available industry templates for onboarding."""
    return {
        "industries": list(INDUSTRY_TEMPLATES.keys()),
        "templates": {
            industry: {
                "service_categories": [cat["name"] for cat in template.get("service_categories", [])],
                "custom_fields": [f["field_name"] for f in template.get("custom_fields", [])],
                "technician_types": [t["role"] for t in template.get("technician_types", [])]
            }
            for industry, template in INDUSTRY_TEMPLATES.items()
        }
    }
