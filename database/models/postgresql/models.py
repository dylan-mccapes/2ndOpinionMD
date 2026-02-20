from sqlalchemy import Column, String, DateTime, Date, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    birthdate = Column(Date, nullable=True)
    subscription_tier = Column(String, nullable=False, server_default="free")
    user_type = Column(String(20), nullable=False, server_default="patient")  # 'patient' | 'doctor'
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # patient's linked doctor
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false")
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, server_default="0")
    locked_until = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_token_expires = Column(DateTime, nullable=True)
    
    journal_entries = relationship("JournalEntry", back_populates="user")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    symptoms = Column(JSON)  # Store as JSON array
    environmental_factors = Column(JSON)  # Store as JSON array
    stress_level = Column(Integer, nullable=True)
    diet_notes = Column(Text, nullable=True)
    sleep_quality = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    analysis = Column(Text, nullable=True)
    pattern_observations = Column(Text, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="journal_entries")

class DoctorPatientInvite(Base):
    __tablename__ = "doctor_patient_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    to_email = Column(String, nullable=False)
    invite_type = Column(String(30), nullable=False)  # 'doctor_invites_patient' | 'patient_invites_doctor'
    token = Column(String, nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="pending")  # 'pending' | 'accepted' | 'declined'
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    from_user = relationship("User", foreign_keys=[from_user_id])


class MedicalKnowledge(Base):
    __tablename__ = "medical_knowledge"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type = Column(String, nullable=False)  # disease, case, condition, etc.
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    icd10_code = Column(String, nullable=True)
    meta_data = Column(JSON)
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
    created_at = Column(DateTime, default=datetime.utcnow)
