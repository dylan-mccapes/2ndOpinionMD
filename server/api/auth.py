from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    birthdate: Optional[date] = None

class User(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    birthdate: Optional[date] = None
    subscription_tier: str = "basic"
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class UserInDB(BaseModel):
    id: str
    email: str
    full_name: str
    hashed_password: str
    subscription_tier: str = "basic"
    created_at: datetime
    is_verified: bool = False
    verification_token: str = None
    verification_token_expires: datetime = None
    failed_login_attempts: int = 0
    locked_until: datetime = None
    password_reset_token: str = None
    password_reset_token_expires: datetime = None
