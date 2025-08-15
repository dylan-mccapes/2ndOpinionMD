
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    birthdate: Optional[date] = None

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    birthdate: Optional[date] = None
    subscription_tier: str = "basic"
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
