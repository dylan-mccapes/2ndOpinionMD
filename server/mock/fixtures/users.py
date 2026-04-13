"""Mock user objects shared across all routers."""
from __future__ import annotations

MOCK_TOKEN = "mock-jwt-lucifer-dev"

DEV_USER = {
    "id": "user-norman-dev",
    "email": "dev@local",
    "full_name": "Norman Eric Roberts",
    "user_type": "patient",
    "is_active": True,
    "is_verified": True,
}

MOCK_DOCTOR = {
    "id": "dr-house-mock",
    "email": "house@ppth.dev",
    "full_name": "Gregory House",
}

MOCK_PATIENT = {
    "id": "user-norman-dev",
    "email": "dev@local",
    "full_name": "Norman Eric Roberts",
    "has_timeline": True,
}
