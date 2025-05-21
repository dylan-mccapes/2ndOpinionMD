import asyncio
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.email.verification import send_verification_email, create_verification_token
from fastapi import Request

async def test_email_sending():
    """Test sending a verification email"""
    print("Testing verification email sending...")
    
    class MockRequest:
        def __init__(self):
            self.headers = {}
            self.base_url = "http://localhost:3000"
    
    mock_request = MockRequest()
    
    token = create_verification_token({"sub": "test@2ndopinionmd.ai"})
    
    try:
        await send_verification_email(
            email="test@2ndopinionmd.ai",
            name="Test User",
            token=token,
            request=mock_request
        )
        print("Verification email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
    
if __name__ == "__main__":
    asyncio.run(test_email_sending())
