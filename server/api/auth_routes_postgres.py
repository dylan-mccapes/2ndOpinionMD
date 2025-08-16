from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
import logging
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

logger = logging.getLogger(__name__)

from server.db.session import get_session
from database.models.postgresql.models import User
from server.api.auth import UserCreate, Token
from pydantic import BaseModel, EmailStr
from datetime import datetime
from sqlalchemy import select, update

class ResendRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    birthdate: Optional[date] = None
    subscription_tier: str
    created_at: datetime

class EmailVerificationInfo(BaseModel):
    queued: bool
    dev_mode: bool
    note: str

class RegistrationResponse(BaseModel):
    user: UserResponse
    email_verification: EmailVerificationInfo
from server.api.auth_postgres import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_user_postgres,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from server.utils.email.verification import send_verification_email, create_verification_token

router = APIRouter()

@router.post("/register", response_model=RegistrationResponse)
async def register_user(user: UserCreate, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    logger.info("Using UserCreate from %s", UserCreate.__module__)
    query = select(User).where(User.email == user.email)
    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    verification_token = str(uuid.uuid4())
    verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    
    hashed_password = get_password_hash(user.password)
    
    try:
        payload = user.dict(exclude_unset=True)        # Pydantic v1
    except AttributeError:
        payload = user.model_dump(exclude_unset=True)  # Pydantic v2
    
    full_name = payload.get("full_name")
    birthdate = payload.get("birthdate")
    
    db_user = User(
        email=user.email,
        full_name=full_name,
        hashed_password=hashed_password,
        birthdate=birthdate,
        verification_token=verification_token,
        verification_token_expires=verification_token_expires
    )
    
    session.add(db_user)
    try:
        await session.commit()
        await session.refresh(db_user)
    except Exception as e:
        await session.rollback()
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        raise
    
    background_tasks.add_task(
        send_verification_email,
        user.email,
        payload.get("full_name") or "User",
        verification_token
    )
    
    return RegistrationResponse(
        user=UserResponse(
            id=str(db_user.id),
            email=db_user.email,
            full_name=db_user.full_name,
            birthdate=db_user.birthdate,
            subscription_tier=db_user.subscription_tier,
            created_at=db_user.created_at,
        ),
        email_verification=EmailVerificationInfo(
            queued=True,
            dev_mode=(os.getenv("EMAIL_DEV_MODE", "0") in ("1", "true", "True", "yes")),
            note="Check your inbox for a verification link. If you don't see it, use 'Resend verification'.",
        )
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "bad_credentials", "message": "Incorrect email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email to continue.",
                "actions": {"resend_endpoint": "/api/auth/resend-verification"}
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token/mobile", response_model=Token)
async def login_for_mobile_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "bad_credentials", "message": "Incorrect email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email to continue.",
                "actions": {"resend_endpoint": "/api/auth/resend-verification"}
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(days=7)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    query = select(User).where(User.verification_token == token)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    if user.verification_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired"
        )
    
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    
    await session.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/forgot-password")
async def forgot_password(email: str, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    query = select(User).where(User.email == email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    reset_token = str(uuid.uuid4())
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    user.password_reset_token = reset_token
    user.password_reset_token_expires = reset_token_expires
    
    await session.commit()
    
    
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password/{token}")
async def reset_password(token: str, new_password: str, session: AsyncSession = Depends(get_session)):
    query = select(User).where(User.password_reset_token == token)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    if user.password_reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired"
        )
    
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None
    
    await session.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/resend-verification")
async def resend_verification(payload: ResendRequest, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    """Resend verification email"""
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"detail": "If an account with that email exists, a verification link has been sent"}
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "already_verified", "message": "Email already verified"}
        )
    
    verification_token = create_verification_token({"sub": user.email})
    token_expires = datetime.utcnow() + timedelta(minutes=30)
    
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(verification_token=verification_token, verification_token_expires=token_expires)
    )
    await session.commit()
    
    background_tasks.add_task(send_verification_email, user.email, user.full_name or "User", verification_token)
    return {"detail": "Verification email sent if the account exists"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user_postgres)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        birthdate=current_user.birthdate,
        subscription_tier=current_user.subscription_tier,
        created_at=current_user.created_at
    )
