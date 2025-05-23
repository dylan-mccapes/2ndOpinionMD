"""
Compatibility layer for pydantic version differences.
This module provides compatibility between different pydantic versions.
"""
from pydantic import SecretStr

Secret = SecretStr
