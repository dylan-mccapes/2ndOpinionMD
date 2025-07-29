import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt
from pathlib import Path
from pydantic import EmailStr

from models.mongodb.auth import SECRET_KEY, ALGORITHM
from utils.email.config import send_email

VERIFICATION_TOKEN_EXPIRE_MINUTES = 30

async def send_verification_email(email: EmailStr, name: str, token: str):
    """
    Send a verification email with a token link
    """
    domain = os.getenv("FRONTEND_URL", "http://localhost:3000")
    verification_url = f"{domain}/verify-email?token={token}"
    
    template_path = Path(__file__).parent.parent.parent / "templates" / "verification.html"
    with open(template_path, "r") as f:
        html_content = f.read()
    
    html_content = html_content.replace("{{ name }}", name)
    html_content = html_content.replace("{{ verification_url }}", verification_url)
    
    text_content = f"""
    Hello {name},
    
    Thank you for registering with 2ndOpinionMD. Please verify your email address by visiting this link:
    
    {verification_url}
    
    This verification link will expire in 30 minutes.
    
    If you didn't create an account with 2ndOpinionMD, please ignore this email.
    """
    
    await send_email(
        subject="Verify Your Email - 2ndOpinionMD",
        recipients=[email],
        body=text_content,
        html_body=html_content
    )

def create_verification_token(data: Dict) -> str:
    """
    Create a verification token similar to JWT tokens
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "purpose": "email_verification"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    Verify a token and return the email if valid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        purpose = payload.get("purpose")
        
        if email is None or purpose != "email_verification":
            return None
            
        return email
    except Exception:
        return None

def create_password_reset_token(data: Dict) -> str:
    """
    Create a password reset token similar to verification tokens
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "purpose": "password_reset"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return the email if valid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        purpose = payload.get("purpose")
        
        if email is None or purpose != "password_reset":
            return None
            
        return email
    except Exception:
        return None

async def send_password_reset_email(email: EmailStr, name: str, token: str):
    """
    Send a password reset email with a token link
    """
    domain = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{domain}/reset-password?token={token}"
    
    template_path = Path(__file__).parent.parent.parent / "templates" / "password_reset.html"
    with open(template_path, "r") as f:
        html_content = f.read()
    
    html_content = html_content.replace("{{ name }}", name)
    html_content = html_content.replace("{{ reset_url }}", reset_url)
    
    text_content = f"""
    Hello {name},
    
    You requested a password reset for your 2ndOpinionMD account. Click the link below to reset your password:
    
    {reset_url}
    
    This link will expire in 30 minutes.
    
    If you didn't request this password reset, please ignore this email.
    """
    
    await send_email(
        subject="Reset Your Password - 2ndOpinionMD",
        recipients=[email],
        body=text_content,
        html_body=html_content
    )
