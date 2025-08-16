from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, EmailStr

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
