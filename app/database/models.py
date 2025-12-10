from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(50), unique=True)
    location = Column(String(500))
    hours = Column(JSON, default={})
    services = Column(JSON, default=[])
    pricing = Column(JSON, default={})
    ai_personality = Column(Text, default="friendly and professional")
    vector_index_id = Column(String(255))
    stripe_customer_id = Column(String(255))
    subscription_status = Column(String(50), default="trial")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    technicians = relationship("Technician", back_populates="business", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="business", cascade="all, delete-orphan")
    knowledgebase_docs = relationship("KnowledgebaseDocument", back_populates="business", cascade="all, delete-orphan")

class Technician(Base):
    __tablename__ = "technicians"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    role = Column(String(100), default="technician")
    is_available = Column(Boolean, default=True)
    skills = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="technicians")

class CallLog(Base):
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
    
    business = relationship("Business", back_populates="call_logs")
    assigned_tech = relationship("Technician")

class KnowledgebaseDocument(Base):
    __tablename__ = "knowledgebase_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String(255))
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = relationship("Business", back_populates="knowledgebase_docs")

class ActiveCall(Base):
    __tablename__ = "active_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(255), unique=True, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    caller_number = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    transcript_buffer = Column(Text, default="")
    status = Column(String(50), default="in_progress")
