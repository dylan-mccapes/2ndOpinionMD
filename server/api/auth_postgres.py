from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from dotenv import load_dotenv

from database.models.postgresql.database import get_db
from database.models.postgresql.models import User
from pydantic import BaseModel
from typing import Optional

class TokenData(BaseModel):
    email: Optional[str] = None

class UserInDB(BaseModel):
    id: str
    email: str
    full_name: str
    hashed_password: str
    birthdate: Optional[str] = None
    subscription_tier: str = "basic"
    created_at: str
    last_login: Optional[str] = None
    is_verified: bool = False
    verification_token: Optional[str] = None
    verification_token_expires: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_token_expires: Optional[str] = None

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user_by_email(email: str, db: AsyncSession):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        return UserInDB(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            birthdate=user.birthdate,
            subscription_tier=user.subscription_tier,
            created_at=user.created_at,
            last_login=user.last_login,
            is_verified=user.is_verified,
            verification_token=user.verification_token,
            verification_token_expires=user.verification_token_expires,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            password_reset_token=user.password_reset_token,
            password_reset_token_expires=user.password_reset_token_expires
        )
    return None

async def authenticate_user(email: str, password: str, db: AsyncSession):
    user = await get_user_by_email(email, db)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        db_user = result.scalar_one_or_none()
        
        if db_user:
            db_user.failed_login_attempts += 1
            
            if db_user.failed_login_attempts >= 5:
                db_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            
            await db.commit()
        
        return False
    
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()
    
    if db_user:
        db_user.failed_login_attempts = 0
        db_user.last_login = datetime.utcnow()
        await db.commit()
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_postgres(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(email=token_data.email, db=db)
    if user is None:
        raise credentials_exception
    
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account locked until {user.locked_until}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
