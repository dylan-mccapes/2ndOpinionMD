from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr

from models.mongodb.models import UserCreate, User, Token, UserInDB
from models.mongodb.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from models.mongodb.database import users_collection

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get JWT token"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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
async def register_user(user: UserCreate):
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
    
    user_in_db = UserInDB(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
    )
    
    await users_collection.insert_one(user_in_db.dict())
    
    return User(
        id=user_in_db.id,
        email=user_in_db.email,
        full_name=user_in_db.full_name,
        subscription_tier=user_in_db.subscription_tier,
        created_at=user_in_db.created_at
    )

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Get current user profile"""
    return User(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        subscription_tier=current_user.subscription_tier,
        created_at=current_user.created_at
    )
