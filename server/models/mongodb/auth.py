from datetime import datetime, timedelta
from typing import Optional
import os
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from models.mongodb.models import UserInDB, TokenData
from models.mongodb.database import users_collection

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password, hashed_password):
    """Verify password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password for storing"""
    return pwd_context.hash(password)

async def get_user(email: str):
    """Get user from database by email"""
    user_dict = await users_collection.find_one({"email": email})
    if user_dict:
        return UserInDB(**user_dict)
    return None

async def authenticate_user(email: str, password: str):
    """Authenticate a user by email and password"""
    from models.mongodb.database import users_collection
    from datetime import datetime, timedelta
    
    user = await get_user(email)
    if not user:
        return False
    
    if user.locked_until and datetime.utcnow() < user.locked_until:
        return "locked"
    
    if not verify_password(password, user.hashed_password):
        failed_attempts = user.failed_login_attempts + 1
        update_data = {"failed_login_attempts": failed_attempts}
        
        if failed_attempts >= 3:
            update_data["locked_until"] = datetime.utcnow() + timedelta(minutes=15)
        
        await users_collection.update_one(
            {"email": email},
            {"$set": update_data}
        )
        
        if failed_attempts >= 3:
            return "locked"
        return False
    
    await users_collection.update_one(
        {"email": email},
        {"$set": {"failed_login_attempts": 0, "locked_until": None}}
    )
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await get_user(email=token_data.email) if token_data.email else None
    if user is None:
        raise credentials_exception
    return user
