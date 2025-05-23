"""
Compatibility layer for fastapi-mail with different pydantic versions.
This module provides compatibility between fastapi-mail and pydantic v2.
"""
from typing import List, Optional, Dict, Any, Union
import os
from pydantic import EmailStr

from pydantic import SecretStr as Secret

class ConnectionConfig:
    """
    Compatible ConnectionConfig class that works with both pydantic v1 and v2.
    This replaces the fastapi-mail ConnectionConfig which has compatibility issues.
    """
    def __init__(
        self,
        MAIL_USERNAME: str,
        MAIL_PASSWORD: str,
        MAIL_FROM: str,
        MAIL_PORT: int,
        MAIL_SERVER: str,
        MAIL_SSL_TLS: bool = True,
        MAIL_STARTTLS: bool = False,
        USE_CREDENTIALS: bool = True,
        VALIDATE_CERTS: bool = True,
        TEMPLATE_FOLDER: Optional[str] = None,
    ):
        self.MAIL_USERNAME = MAIL_USERNAME
        self.MAIL_PASSWORD = MAIL_PASSWORD
        self.MAIL_FROM = MAIL_FROM
        self.MAIL_PORT = MAIL_PORT
        self.MAIL_SERVER = MAIL_SERVER
        self.MAIL_SSL_TLS = MAIL_SSL_TLS
        self.MAIL_STARTTLS = MAIL_STARTTLS
        self.USE_CREDENTIALS = USE_CREDENTIALS
        self.VALIDATE_CERTS = VALIDATE_CERTS
        self.TEMPLATE_FOLDER = TEMPLATE_FOLDER

class MessageSchema:
    """
    Compatible MessageSchema class that works with both pydantic v1 and v2.
    This replaces the fastapi-mail MessageSchema which has compatibility issues.
    """
    def __init__(
        self,
        subject: str,
        recipients: List[EmailStr],
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[EmailStr]] = None,
        bcc: Optional[List[EmailStr]] = None,
        subtype: str = "plain",
        charset: str = "utf-8",
    ):
        self.subject = subject
        self.recipients = recipients
        self.body = body
        self.html = html or body
        self.attachments = attachments or []
        self.cc = cc or []
        self.bcc = bcc or []
        self.subtype = subtype
        self.charset = charset

try:
    from fastapi_mail import FastMail as OriginalFastMail
    
    class FastMail:
        """
        Compatible FastMail class that works with our ConnectionConfig and MessageSchema.
        """
        def __init__(self, config: ConnectionConfig):
            from fastapi_mail import ConnectionConfig as OriginalConnectionConfig
            
            original_config = OriginalConnectionConfig(
                MAIL_USERNAME=config.MAIL_USERNAME,
                MAIL_PASSWORD=config.MAIL_PASSWORD,
                MAIL_FROM=config.MAIL_FROM,
                MAIL_PORT=config.MAIL_PORT,
                MAIL_SERVER=config.MAIL_SERVER,
                MAIL_SSL_TLS=config.MAIL_SSL_TLS,
                MAIL_STARTTLS=config.MAIL_STARTTLS,
                USE_CREDENTIALS=config.USE_CREDENTIALS,
                VALIDATE_CERTS=config.VALIDATE_CERTS,
                TEMPLATE_FOLDER=config.TEMPLATE_FOLDER
            )
            
            self._fastmail = OriginalFastMail(original_config)
        
        async def send_message(self, message: MessageSchema):
            from fastapi_mail import MessageSchema as OriginalMessageSchema
            
            original_message = OriginalMessageSchema(
                subject=message.subject,
                recipients=message.recipients,
                body=message.body,
                html=message.html,
                attachments=message.attachments,
                cc=message.cc,
                bcc=message.bcc,
                subtype=message.subtype,
                charset=message.charset
            )
            
            await self._fastmail.send_message(original_message)
            
except ImportError:
    class FastMail:
        def __init__(self, config: ConnectionConfig):
            self.config = config
        
        async def send_message(self, message: MessageSchema):
            print(f"Would send email to {message.recipients} with subject '{message.subject}'")
            print(f"Body: {message.body}")
