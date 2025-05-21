import os
from typing import List, Set
from pathlib import Path

ALLOWED_EMAILS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "allowed_emails.txt")

def load_allowed_emails() -> Set[str]:
    """
    Load the list of allowed email addresses from the allowed_emails.txt file
    
    Returns:
        Set of allowed email addresses
    """
    allowed_emails = set()
    
    if os.path.exists(ALLOWED_EMAILS_PATH):
        with open(ALLOWED_EMAILS_PATH, "r") as f:
            for line in f:
                email = line.strip()
                if email and not email.startswith("#"):  # Skip empty lines and comments
                    allowed_emails.add(email.lower())
    
    return allowed_emails

def is_email_allowed(email: str) -> bool:
    """
    Check if an email is in the allowed list
    
    Args:
        email: Email address to check
        
    Returns:
        True if the email is in the allowed list, False otherwise
    """
    allowed_emails = load_allowed_emails()
    return email.lower() in allowed_emails

def add_email_to_allowlist(email: str) -> bool:
    """
    Add an email to the allowed list
    
    Args:
        email: Email address to add
        
    Returns:
        True if the email was added, False if it was already in the list
    """
    allowed_emails = load_allowed_emails()
    
    if email.lower() in allowed_emails:
        return False
    
    with open(ALLOWED_EMAILS_PATH, "a") as f:
        f.write(f"{email}\n")
    
    return True
