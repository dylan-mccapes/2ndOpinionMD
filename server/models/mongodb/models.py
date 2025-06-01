from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    email: str
    full_name: str
    
class UserCreate(UserBase):
    password: str
    
class UserInDB(UserBase):
    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    hashed_password: str
    subscription_tier: str = "basic"  # basic, premium, professional
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
<<<<<<< HEAD
    
=======
    is_verified: bool = False
    verification_token: Optional[str] = None
    verification_token_expires: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_token_expires: Optional[datetime] = None

>>>>>>> 417ae9ae (Implement password reset functionality with complexity validation and failed login tracking)
class User(UserBase):
    id: str
    subscription_tier: str
    created_at: datetime
    
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    email: Optional[str] = None
    
class SymptomEntry(BaseModel):
    symptom: str
    severity: int = Field(ge=1, le=10)  # 1-10 scale
    
class EnvironmentalFactor(BaseModel):
    factor_type: str  # food, stress, product, etc.
    description: str
    
class JournalEntryBase(BaseModel):
    date: datetime = Field(default_factory=datetime.now)
    symptoms: List[SymptomEntry]
    environmental_factors: Optional[List[EnvironmentalFactor]] = []
    stress_level: Optional[int] = Field(None, ge=1, le=10)  # 1-10 scale
    diet_notes: Optional[str] = None
    sleep_quality: Optional[int] = Field(None, ge=1, le=10)  # 1-10 scale
    notes: Optional[str] = None
    
class JournalEntryCreate(JournalEntryBase):
    pass
    
class JournalEntry(JournalEntryBase):
    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
