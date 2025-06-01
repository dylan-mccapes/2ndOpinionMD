from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, BaseModel
import logging

from database.models.postgresql.models import User as DBUser
from server.api.auth_postgres import (
    authenticate_user, 
    create_access_token, 
    get_current_user_postgres as get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_user_by_email
)
<<<<<<< HEAD
from database.models.postgresql.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from datetime import datetime, timedelta
class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

class User(BaseModel):
    id: str
    email: str
    full_name: str
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

from server.utils.rate_limiter import auth_rate_limiter
from server.utils.email.verification import send_verification_email, create_verification_token, verify_token, send_password_reset_email, create_password_reset_token, verify_password_reset_token
from server.utils.email_allowlist import is_email_allowed
from server.utils.password_validation import validate_password_complexity
=======
from models.mongodb.database import users_collection
from utils.rate_limiter import auth_rate_limiter
from utils.email.verification import send_verification_email, create_verification_token, verify_token, send_password_reset_email, create_password_reset_token, verify_password_reset_token
from utils.email_allowlist import is_email_allowed
from utils.password_validation import validate_password_complexity
>>>>>>> 417ae9ae (Implement password reset functionality with complexity validation and failed login tracking)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(auth_rate_limiter), db: AsyncSession = Depends(get_db)):
    """Login endpoint to get JWT token"""
<<<<<<< HEAD
    user = await authenticate_user(form_data.username, form_data.password, db)
=======
    user = await authenticate_user(form_data.username, form_data.password)
>>>>>>> 417ae9ae (Implement password reset functionality with complexity validation and failed login tracking)
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
    await db.execute(query)
    await db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/mobile-token", response_model=Token)
async def login_for_mobile_access_token(form_data: OAuth2PasswordRequestForm = Depends(), _: None = Depends(auth_rate_limiter)):
    """Login endpoint to get long-lasting JWT token for mobile apps"""
    user = await authenticate_user(form_data.username, form_data.password)
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
        
    access_token_expires = timedelta(days=7)
    access_token = create_access_token(
        data={"sub": user.email, "mobile": True}, expires_delta=access_token_expires
    )
    
    await users_collection.update_one(
        {"email": user.email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=User)
async def register_user(user: UserCreate, request: Request, _: None = Depends(auth_rate_limiter)):
    """Register a new user"""
    password_errors = validate_password_complexity(user.password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "errors": password_errors}
        )
    
    if not (user.email.endswith("@2ndopinionmd.ai") or is_email_allowed(user.email)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not authorized for registration. Please use a 2ndopinionmd.ai email or contact support."
        )
        
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        existing_user_obj = UserInDB(**existing_user)
        
        if existing_user_obj.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if (existing_user_obj.verification_token_expires and 
            datetime.utcnow() > existing_user_obj.verification_token_expires):
            
            verification_token = create_verification_token({"sub": user.email})
            token_expires = datetime.utcnow() + timedelta(minutes=30)
            
            await users_collection.update_one(
                {"email": user.email},
                {"$set": {
                    "full_name": user.full_name,
                    "hashed_password": get_password_hash(user.password),
                    "verification_token": verification_token,
                    "verification_token_expires": token_expires,
                    "failed_login_attempts": 0,
                    "locked_until": None
                }}
            )
            
            await send_verification_email(
                email=user.email,
                name=user.full_name,
                token=verification_token,
                request=request
            )
            
            return User(
                id=existing_user_obj.id,
                email=user.email,
                full_name=user.full_name,
                subscription_tier=existing_user_obj.subscription_tier,
                created_at=existing_user_obj.created_at
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered but not verified. Please check your email for verification link or request a new one."
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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
async def forgot_password(request_data: ForgotPasswordRequest, request: Request, _: None = Depends(auth_rate_limiter)):
    """Send password reset email"""
    user_dict = await users_collection.find_one({"email": request_data.email})
    if not user_dict:
        return {"detail": "If an account with that email exists, a password reset link has been sent"}
        
    user = UserInDB(**user_dict)
    
    reset_token = create_password_reset_token({"sub": request_data.email})
    token_expires = datetime.utcnow() + timedelta(minutes=30)
    
    await users_collection.update_one(
        {"email": request_data.email},
        {"$set": {
            "password_reset_token": reset_token,
            "password_reset_token_expires": token_expires
        }}
    )
    
    await send_password_reset_email(
        email=request_data.email,
        name=user.full_name,
        token=reset_token,
        request=request
    )
    
    return {"detail": "If an account with that email exists, a password reset link has been sent"}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(request_data: ResetPasswordRequest, _: None = Depends(auth_rate_limiter)):
    """Reset password with token"""
    password_errors = validate_password_complexity(request_data.new_password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "errors": password_errors}
        )
    
    email = verify_password_reset_token(request_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
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
            "hashed_password": get_password_hash(request_data.new_password),
            "password_reset_token": None,
            "password_reset_token_expires": None,
            "failed_login_attempts": 0,
            "locked_until": None
        }}
    )
    
    return {"detail": "Password reset successfully"}
