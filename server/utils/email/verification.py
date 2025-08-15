import os
import smtplib
import ssl
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt
from pathlib import Path
from pydantic import EmailStr
from email.message import EmailMessage
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
ALGORITHM = "HS256"
from server.utils.email.config import send_email

VERIFICATION_TOKEN_EXPIRE_MINUTES = 30
logger = logging.getLogger(__name__)

def build_verification_link(token: str) -> str:
    """Build verification link using FRONTEND_ORIGIN environment variable"""
    origin = os.getenv("FRONTEND_ORIGIN") or os.getenv("FRONTEND_URL") or "https://2ndopinionmd.ai"
    return f"{origin}/verify-email?token={token}"

async def send_verification_email(email: EmailStr, name: str, token: str):
    """
    Send a verification email with a token link
    """
    dev_mode = os.getenv("EMAIL_DEV_MODE", "0") in ("1", "true", "True", "yes")
    verification_url = build_verification_link(token)
    
    if dev_mode:
        logger.warning("[DEV-MODE] Verification email not sent. Link: %s", verification_url)
        return
    
    email_provider = os.getenv("EMAIL_PROVIDER", "fastmail").lower()
    
    if email_provider == "smtp":
        await _send_smtp_verification_email(email, name, verification_url)
    else:
        await _send_fastmail_verification_email(email, name, verification_url)

async def _send_fastmail_verification_email(email: EmailStr, name: str, verification_url: str):
    """Send verification email using FastMail (existing implementation)"""
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

async def _send_smtp_verification_email(email: EmailStr, name: str, verification_url: str):
    """Send verification email using SMTP"""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    use_tls = os.getenv("SMTP_TLS", "1") in ("1", "true", "True", "yes")
    from_addr = os.getenv("EMAIL_FROM", "no-reply@2ndopinionmd.ai")
    
    if not (host and user and pwd):
        logger.error("SMTP not configured; logging link instead")
        logger.warning("Verification link for %s: %s", email, verification_url)
        return
    
    msg = EmailMessage()
    msg["Subject"] = "Verify your 2ndOpinionMD account"
    msg["From"] = from_addr
    msg["To"] = email
    msg.set_content(f"Hi {name or 'there'},\n\nVerify your email:\n{verification_url}\n")
    
    if use_tls:
        with smtplib.SMTP(host, port) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            s.login(user, pwd)
            s.send_message(msg)
    
    logger.info("Sent verification email to %s", email)

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
