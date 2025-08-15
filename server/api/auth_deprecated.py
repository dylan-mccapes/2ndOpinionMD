from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, BaseModel
import logging

from server.api.auth import UserCreate, Token, User

from database.models.postgresql.models import User as DBUser
from server.api.auth_postgres import (
    authenticate_user, 
    create_access_token, 
    get_current_user_postgres as get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_user_by_email
)
from server.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional
from datetime import date
from datetime import datetime, timedelta


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

from server.utils.rate_limiter import auth_rate_limiter
from server.utils.email.verification import send_verification_email, create_verification_token, verify_token, send_password_reset_email, create_password_reset_token, verify_password_reset_token
from server.utils.email_allowlist import is_email_allowed
from server.utils.password_validation import validate_password_complexity

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(auth_rate_limiter), session: AsyncSession = Depends(get_session)):
    """Login endpoint to get JWT token"""
    user = await authenticate_user(form_data.username, form_data.password, session)
    if user == "locked":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account locked due to too many failed login attempts. Please reset your password or wait 15 minutes.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your email for verification link.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    query = update(DBUser).where(DBUser.email == user.email).values(last_login=datetime.utcnow())
    await session.execute(query)
    await session.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/mobile-token", response_model=Token)
async def login_for_mobile_access_token(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(auth_rate_limiter)):
    """Login endpoint to get long-lasting JWT token for mobile apps"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

@router.post("/register", response_model=User)
async def register_user(user: UserCreate, request: Request, _: None = Depends(auth_rate_limiter)):
    """Register a new user"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user), _: None = Depends(auth_rate_limiter)):
    """Get current user profile"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

@router.get("/verify-email")
async def verify_email(token: str):
    """Verify email address with token"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

@router.post("/resend-verification")
async def resend_verification(email: EmailStr, request: Request, _: None = Depends(auth_rate_limiter)):
    """Resend verification email"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
async def forgot_password(request_data: ForgotPasswordRequest, request: Request, _: None = Depends(auth_rate_limiter)):
    """Send password reset email"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(request_data: ResetPasswordRequest, _: None = Depends(auth_rate_limiter)):
    """Reset password with token"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MongoDB implementation deprecated. Use PostgreSQL auth endpoints."
    )
