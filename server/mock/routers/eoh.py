from fastapi import APIRouter
from server.mock.fixtures.flare_report import FLARE_REPORT
from server.mock.fixtures.router_plan import ROUTER_PLAN

router = APIRouter(prefix="/api/eoh", tags=["eoh"])


@router.post("/router_plan")
async def router_plan(body: dict = None):
    question = (body or {}).get("question", "")
    return {
        **ROUTER_PLAN,
        "_mock_question": question,
    }


@router.get("/flarereport/{patient_id}")
async def flare_report(patient_id: str):
    return {**FLARE_REPORT, "patient_id": patient_id}


@router.get("/landscape/{patient_id}")
async def landscape(patient_id: str):
    return {
        "patient_id": patient_id,
        "landscape": FLARE_REPORT["probabilistic_differential"],
        "generated_at": "2025-12-10T00:00:00Z",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "mock": True}
