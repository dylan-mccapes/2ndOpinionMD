from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
import logging

from models.mongodb.models import UserCreate, User, Token, UserInDB
from models.mongodb.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from models.mongodb.database import users_collection
from utils.rate_limiter import auth_rate_limiter
from utils.email.verification import send_verification_email, create_verification_token, verify_token

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(auth_rate_limiter)):
    """Login endpoint to get JWT token"""
    user = await authenticate_user(form_data.username, form_data.password)
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
    
    await users_collection.update_one(
        {"email": user.email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=User)
async def register_user(user: UserCreate, request: Request, _: None = Depends(auth_rate_limiter)):
    """Register a new user"""
    if not user.email.endswith("@2ndopinionmd.ai"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 2ndopinionmd.ai email addresses are allowed to register"
        )
        
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    verification_token = create_verification_token({"sub": user.email})
    token_expires = datetime.utcnow() + timedelta(minutes=30)
    
    user_in_db = UserInDB(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=token_expires
    )
    
    await users_collection.insert_one(user_in_db.dict())
    
    await send_verification_email(
        email=user.email,
        name=user.full_name,
        token=verification_token,
        request=request
    )
    
    return User(
        id=user_in_db.id,
        email=user_in_db.email,
        full_name=user_in_db.full_name,
        subscription_tier=user_in_db.subscription_tier,
        created_at=user_in_db.created_at
    )

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user), _: None = Depends(auth_rate_limiter)):
    """Get current user profile"""
    return User(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        subscription_tier=current_user.subscription_tier,
        created_at=current_user.created_at
    )

@router.get("/verify-email")
async def verify_email(token: str):
    """Verify email address with token"""
    email = verify_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
        
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    await users_collection.update_one(
        {"email": email},
        {"$set": {
            "is_verified": True,
            "verification_token": None,
            "verification_token_expires": None
        }}
    )
    
    return {"detail": "Email verified successfully"}

@router.post("/resend-verification")
async def resend_verification(email: EmailStr, request: Request, _: None = Depends(auth_rate_limiter)):
    """Resend verification email"""
    user_dict = await users_collection.find_one({"email": email})
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    user = UserInDB(**user_dict)
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
        
    verification_token = create_verification_token({"sub": email})
    token_expires = datetime.utcnow() + timedelta(minutes=30)
    
    await users_collection.update_one(
        {"email": email},
        {"$set": {
            "verification_token": verification_token,
            "verification_token_expires": token_expires
        }}
    )
    
    await send_verification_email(
        email=email,
        name=user.full_name,
        token=verification_token,
        request=request
    )
    
    return {"detail": "Verification email sent"}
