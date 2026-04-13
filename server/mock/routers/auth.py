from fastapi import APIRouter
from fastapi.responses import JSONResponse
from server.mock.fixtures.users import DEV_USER, MOCK_TOKEN

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(body: dict = None):
    return {**DEV_USER, "access_token": MOCK_TOKEN, "token_type": "bearer"}


@router.post("/token")
async def token(body: dict = None):
    return {"access_token": MOCK_TOKEN, "token_type": "bearer"}


@router.get("/me")
@router.get("/users/me")
async def me():
    return DEV_USER


@router.get("/verify-email")
async def verify_email(token: str = ""):
    return {"verified": True}


@router.post("/forgot-password")
async def forgot_password(body: dict = None):
    return {"sent": True}


@router.post("/reset-password/{token}")
async def reset_password(token: str, body: dict = None):
    return {"reset": True}


@router.post("/resend-verification")
async def resend_verification(body: dict = None):
    return {"sent": True}


@router.post("/accept-doctor-invite")
async def accept_doctor_invite(body: dict = None):
    return {"accepted": True}


@router.post("/accept-patient-invite")
async def accept_patient_invite(body: dict = None):
    return {"accepted": True}
