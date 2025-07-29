import os
from pydantic import EmailStr
from typing import List
from dotenv import load_dotenv
from utils.email.fastapi_mail_compat import FastMail, MessageSchema, ConnectionConfig

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("REPORT_EMAIL_FROM", "nate@2ndopinionmd.ai"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "True").lower() == "true",
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS", "True").lower() == "true",
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS", "True").lower() == "true",
    TEMPLATE_FOLDER=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"),
)

async def send_email(subject: str, recipients: List[EmailStr], body: str, html_body: str = None):
    """
    Send an email with the configured mail settings
    """
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        html=html_body or body,
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)
