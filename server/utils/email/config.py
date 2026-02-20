import os
import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
from dotenv import load_dotenv
from server.utils.email.pydantic_compat import Secret  # Add compatibility layer

load_dotenv()
logger = logging.getLogger(__name__)

# Port 587: use STARTTLS only (aiosmtplib rejects both use_tls and start_tls).
# Port 465: set MAIL_SSL_TLS=true and MAIL_STARTTLS=false in env.
_conf_ssl = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
_conf_starttls = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("REPORT_EMAIL_FROM", "dylan@2ndopinionmd.ai"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_SSL_TLS=_conf_ssl,
    MAIL_STARTTLS=_conf_starttls if not _conf_ssl else False,
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
