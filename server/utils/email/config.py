import os
import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
from dotenv import load_dotenv
from server.utils.email.pydantic_compat import Secret  # Add compatibility layer

load_dotenv()
logger = logging.getLogger(__name__)

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

async def send_email(
    subject: str,
    recipients: List[EmailStr],
    *,
    html_body: str | None = None,
    text_body: str | None = None,
    body: str = None  # Keep for backward compatibility
) -> None:
    """
    Send an email with the configured mail settings
    """
    email_body = html_body if html_body else (text_body or body or "")
    subtype = "html" if html_body else "plain"

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=email_body,
        subtype=subtype,  # REQUIRED on pydantic v2 / fastapi-mail
    )
    
    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info("Email enqueued to %s with subtype=%s", recipients, subtype)
    except Exception:
        logger.exception("Email send failed for %s", recipients)
