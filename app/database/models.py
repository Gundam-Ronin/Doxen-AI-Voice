from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import datetime
import uuid

Base = declarative_base()


class Business(Base):
    """Universal Business Profile - supports ANY home service industry"""
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    owner_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Industry & Contact
    industry = Column(String(100), default="general")  # HVAC, Plumbing, Electrical, Cleaning, Pest, etc.
    phone_number = Column(String(50), unique=True)
    email = Column(String(255))
    address = Column(Text)
    location = Column(String(500))
    
    # Coverage & Hours
    coverage_area = Column(JSON, default=[])  # List of zip codes
    hours = Column(JSON, default={})  # {"mon": ["08:00-17:00"], "tue": [...]}
    business_hours = Column(JSON, default={})  # Alias for universal schema compatibility
    
    # Services & Pricing
    services = Column(JSON, default=[])  # Legacy field
    pricing = Column(JSON, default={})
    pricing_rules = Column(JSON, default={})  # {"flat_rate": false, "dynamic": true, ...}
    
    # Dispatch Configuration
    dispatch_rules = Column(JSON, default={
        "mode": "skill_based",  # round_robin, skill_based, location_based, manual
        "max_distance_miles": 25,
        "auto_dispatch_enabled": True
    })
    
    # Custom Fields (industry-specific)
    custom_fields = Column(JSON, default=[])  # [{"field_name": "Gate Code", "type": "string"}, ...]
    
    # Technician Types/Roles
    technician_types = Column(JSON, default=[])  # [{"role": "HVAC", "skills": [...]}, ...]
    
    # AI & Personality
    ai_personality = Column(Text, default="friendly and professional")
    
    # Integrations
    vector_index_id = Column(String(255))
    knowledgebase_id = Column(String(255))
    calendar_integration = Column(JSON, default={})  # {"google_calendar_id": "..."}
    mailchimp_integration = Column(JSON, default={})
    sendgrid_integration = Column(JSON, default={})
    
    # Billing
    stripe_customer_id = Column(String(255))
    subscription_status = Column(String(50), default="trial")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    technicians = relationship("Technician", back_populates="business", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="business", cascade="all, delete-orphan")
    knowledgebase_docs = relationship("KnowledgebaseDocument", back_populates="business", cascade="all, delete-orphan")
    service_categories = relationship("ServiceCategory", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="business", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="business", cascade="all, delete-orphan")
    business_settings = relationship("BusinessSetting", back_populates="business", cascade="all, delete-orphan")


class ServiceCategory(Base):
    """Universal Service Categories - each business defines their own"""
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    name = Column(String(255), nullable=False)  # "AC Repair", "Drain Cleaning", etc.
    description = Column(Text)
    sub_services = Column(JSON, default=[])  # ["Filter Replacement", "Leak Repair", ...]
    required_fields = Column(JSON, default=[])  # ["name", "address", "system_type"]
    default_duration_minutes = Column(Integer, default=60)
    allow_urgent = Column(Boolean, default=True)
    extra_data = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="service_categories")
    appointments = relationship("Appointment", back_populates="service_category")


class Technician(Base):
    """Universal Technician/Crew/Staff - any type of service worker"""
    __tablename__ = "technicians"
    
    id = Column(Integer, primary_key=True, index=True)
    technician_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255))
    
    # Role & Skills
    role = Column(String(100), default="technician")  # technician, crew_lead, inspector, etc.
    skills = Column(JSON, default=[])  # ["AC Repair", "Heating", "Electrical", ...]
    
    # Location & Coverage
    home_zip = Column(String(20))
    service_radius_miles = Column(Integer, default=25)
    
    # Availability
    is_available = Column(Boolean, default=True)
    availability = Column(JSON, default={})  # {"mon": ["08:00-17:00"], ...}
    status = Column(String(50), default="active")  # active, off, vacation, busy
    
    # Calendar
    calendar_reference = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="technicians")
    dispatch_logs = relationship("DispatchLog", back_populates="technician")
    appointments = relationship("Appointment", back_populates="technician")


class Customer(Base):
    """Universal Customer/Lead - every caller becomes a lead"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    # Contact Info
    name = Column(String(255))
    phone_number = Column(String(50))
    email = Column(String(255))
    address = Column(Text)
    zip_code = Column(String(20))
    
    # Dynamic Fields (industry-specific data)
    extra_data = Column(JSON, default={})  # {"gate_code": "1234", "home_type": "House", ...}
    
    # CRM Fields
    lead_score = Column(Integer, default=0)
    customer_type = Column(String(50), default="lead")  # lead, prospect, customer, vip
    source = Column(String(100), default="phone")  # phone, web, referral, ad
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = relationship("Business", back_populates="customers")
    appointments = relationship("Appointment", back_populates="customer")
    calls = relationship("Call", back_populates="customer")


class Appointment(Base):
    """Universal Appointment - works for any service type"""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    
    # Service Details
    service_type = Column(String(255))
    sub_service = Column(String(255))
    
    # Scheduling
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer, default=60)
    
    # Urgency & Status
    urgency_level = Column(String(50), default="normal")  # normal, high, emergency
    status = Column(String(50), default="booked")  # booked, confirmed, in_progress, completed, canceled, no_show
    
    # Details
    customer_notes = Column(Text)
    internal_notes = Column(Text)
    extra_data = Column(JSON, default={})  # Dynamic fields
    
    # Calendar Integration
    google_event_id = Column(String(255))
    
    # Source Tracking
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = relationship("Business", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
    service_category = relationship("ServiceCategory", back_populates="appointments")
    technician = relationship("Technician", back_populates="appointments")
    dispatch_logs = relationship("DispatchLog", back_populates="appointment")


class Call(Base):
    """Universal Call Log - comprehensive call tracking"""
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    call_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    call_sid = Column(String(255), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Call Details
    caller_phone = Column(String(50))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer, default=0)
    
    # Outcome & Analysis
    outcome = Column(String(100))  # appointment_booked, lead_captured, info_request, no_answer, hangup, voicemail
    sentiment_score = Column(Float)
    sentiment = Column(String(50))  # positive, neutral, negative
    
    # Recordings & Transcripts
    recording_url = Column(String(500))
    transcript = Column(Text)
    call_summary = Column(Text)
    
    # AI Extraction Results
    extracted_fields = Column(JSON, default={})  # All extracted customer data
    intents = Column(JSON, default=[])  # [{"intent": "book_appointment", "confidence": 0.95}, ...]
    
    # Disposition
    disposition = Column(String(100))
    is_emergency = Column(Boolean, default=False)
    language = Column(String(10), default="en")
    
    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="calls")
    customer = relationship("Customer", back_populates="calls")
    transcripts = relationship("CallTranscript", back_populates="call", cascade="all, delete-orphan")
    appointments = relationship("Appointment", backref="source_call")


class CallTranscript(Base):
    """Real-time transcript entries for calls"""
    __tablename__ = "call_transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String(50))  # "customer", "cortana", "system"
    text = Column(Text)
    
    call = relationship("Call", back_populates="transcripts")


class DispatchLog(Base):
    """Track technician dispatch events"""
    __tablename__ = "dispatch_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    dispatch_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    
    dispatch_mode = Column(String(50))  # round_robin, skill_based, location_based, manual
    status = Column(String(50), default="sent")  # sent, acknowledged, en_route, arrived, completed, canceled
    message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    appointment = relationship("Appointment", back_populates="dispatch_logs")
    technician = relationship("Technician", back_populates="dispatch_logs")


class EmailLog(Base):
    """Track all email communications"""
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    email_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    email_type = Column(String(100))  # confirmation, follow_up, reminder, quote, review_request
    provider = Column(String(50))  # mailchimp, sendgrid
    to_email = Column(String(255))
    subject = Column(String(500))
    status = Column(String(50))  # sent, delivered, opened, clicked, bounced, failed
    payload = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SmsLog(Base):
    """Track all SMS communications"""
    __tablename__ = "sms_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sms_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    to_number = Column(String(50))
    from_number = Column(String(50))
    message = Column(Text)
    sms_type = Column(String(100))  # confirmation, dispatch, reminder, follow_up
    status = Column(String(50))  # queued, sent, delivered, failed
    twilio_sid = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BusinessSetting(Base):
    """Dynamic business settings/overrides"""
    __tablename__ = "business_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    setting_key = Column(String(255), nullable=False)
    setting_value = Column(JSON)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('business_id', 'setting_key', name='uix_business_setting'),
    )
    
    business = relationship("Business", back_populates="business_settings")


# Legacy models for backward compatibility
class CallLog(Base):
    """Legacy Call Log - kept for backward compatibility"""
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    call_sid = Column(String(255), unique=True)
    caller_number = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration = Column(Integer, default=0)
    transcript = Column(Text)
    summary = Column(Text)
    sentiment = Column(String(50))
    disposition = Column(String(100))
    booked_appointment = Column(Boolean, default=False)
    appointment_time = Column(DateTime, nullable=True)
    assigned_tech_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    is_emergency = Column(Boolean, default=False)
    language = Column(String(10), default="en")
    
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_email = Column(String(255), nullable=True)
    customer_address = Column(Text, nullable=True)
    service_requested = Column(String(255), nullable=True)
    
    business = relationship("Business", back_populates="call_logs")
    assigned_tech = relationship("Technician")


class KnowledgebaseDocument(Base):
    """Knowledgebase Documents with vector search support"""
    __tablename__ = "knowledgebase_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String(255))
    category = Column(String(100))  # faq, pricing, service, policy, promotion, etc.
    
    # Metadata for search
    tags = Column(JSON, default=[])
    extra_data = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = relationship("Business", back_populates="knowledgebase_docs")


class ActiveCall(Base):
    """Track active/in-progress calls"""
    __tablename__ = "active_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(255), unique=True, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    caller_number = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    transcript_buffer = Column(Text, default="")
    status = Column(String(50), default="in_progress")
    
    # Phase 6 additions
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    extracted_data = Column(JSON, default={})
    detected_intents = Column(JSON, default=[])
