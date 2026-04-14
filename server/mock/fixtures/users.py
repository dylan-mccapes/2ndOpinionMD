"""Mock user objects shared across all routers."""
from __future__ import annotations

from server.mock.config import mock_user_type

MOCK_TOKEN = "mock-jwt-lucifer-dev"

DEV_USER_PATIENT = {
    "id": "user-norman-dev",
    "email": "dev@local",
    "full_name": "Norman Eric Roberts",
    "user_type": "patient",
    "is_active": True,
    "is_verified": True,
}

DEV_USER_DOCTOR = {
    "id": "dr-house-mock",
    "email": "house@ppth.dev",
    "full_name": "Gregory House",
    "user_type": "doctor",
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


def get_dev_user() -> dict:
    return DEV_USER_DOCTOR if mock_user_type() == "doctor" else DEV_USER_PATIENT
