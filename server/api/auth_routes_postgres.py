from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

from database.models.postgresql.database import get_db
from database.models.postgresql.models import User
from database.models.postgresql.models import UserCreate, User as UserResponse, Token
from server.api.auth_postgres import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_user_postgres,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from server.utils.email.verification import send_verification_email
from pydantic import EmailStr

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == user.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    verification_token = str(uuid.uuid4())
    verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        birthdate=user.birthdate,
        verification_token=verification_token,
        verification_token_expires=verification_token_expires
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.full_name,
        verification_token
    )
    
    return UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        full_name=db_user.full_name,
        birthdate=db_user.birthdate,
        subscription_tier=db_user.subscription_tier,
        created_at=db_user.created_at
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(form_data.username, form_data.password, db)
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
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token/mobile", response_model=Token)
async def login_for_mobile_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(form_data.username, form_data.password, db)
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
    
    access_token_expires = timedelta(days=7)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.verification_token == token)
    result = await db.execute(query)
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
    
    await db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/forgot-password")
async def forgot_password(email: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    reset_token = str(uuid.uuid4())
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    user.password_reset_token = reset_token
    user.password_reset_token_expires = reset_token_expires
    
    await db.commit()
    
    
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password/{token}")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.password_reset_token == token)
    result = await db.execute(query)
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
    
    await db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/resend-verification")
async def resend_verification(email: EmailStr, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Resend verification email"""
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification_token = str(uuid.uuid4())
    verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    
    user.verification_token = verification_token
    user.verification_token_expires = verification_token_expires
    
    await db.commit()
    
    background_tasks.add_task(
        send_verification_email,
        email,
        user.full_name,
        verification_token
    )
    
    return {"message": "Verification email sent"}

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
