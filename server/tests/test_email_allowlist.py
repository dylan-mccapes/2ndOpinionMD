import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from server.utils.email_allowlist import load_allowed_emails, is_email_allowed, add_email_to_allowlist

def test_load_allowed_emails():
    """Test loading allowed emails from file"""
    allowed_emails = load_allowed_emails()
    print(f"Loaded {len(allowed_emails)} allowed emails: {allowed_emails}")
    
    assert "jacquelinewall@rocketmail.com" in allowed_emails
    
def test_is_email_allowed():
    """Test checking if an email is allowed"""
    assert is_email_allowed("jacquelinewall@rocketmail.com") == True
    
    assert is_email_allowed("random@example.com") == False
    
    assert is_email_allowed("JacquelineWall@RocketMail.com") == True
    
def test_add_email_to_allowlist():
    """Test adding an email to the allowed list"""
    test_email = "test_allowlist@example.com"
    
    if is_email_allowed(test_email):
        print(f"{test_email} is already in the allowlist")
    else:
        result = add_email_to_allowlist(test_email)
        assert result == True
        
        assert is_email_allowed(test_email) == True
        
        print(f"Successfully added {test_email} to the allowlist")
    
if __name__ == "__main__":
    test_load_allowed_emails()
    test_is_email_allowed()
    test_add_email_to_allowlist()
