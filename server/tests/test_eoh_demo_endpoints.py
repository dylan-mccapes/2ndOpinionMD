# server/tests/test_eoh_demo_endpoints.py
"""
Unit tests for the EoH demo endpoints.

Tests the /api/eoh_demo/* endpoints for multi-patient demo data.
"""

import pytest
from fastapi.testclient import TestClient

from server.api.app_postgres import app
from server.api.eoh_demo_data import (
    DEMO_PATIENTS,
    DEMO_TIMELINES,
    get_patient,
    get_patient_list,
    get_timeline,
)


client = TestClient(app)


class TestEoHDemoData:
    """Tests for the eoh_demo_data module."""

    def test_demo_patients_has_four_patients(self):
        """Test that DEMO_PATIENTS contains exactly 4 patients."""
        assert len(DEMO_PATIENTS) == 4
        assert "P1" in DEMO_PATIENTS
        assert "P2" in DEMO_PATIENTS
        assert "P3" in DEMO_PATIENTS
        assert "P4" in DEMO_PATIENTS

    def test_demo_patient_structure(self):
        """Test that each patient has the required fields."""
        required_fields = {
            "id", "label", "summary", "diagnosis", "age", "sex",
            "serostatus", "meds", "recent_labs", "das28_history",
            "recent_flares", "journal_highlights"
        }

        for pid, patient in DEMO_PATIENTS.items():
            for field in required_fields:
                assert field in patient, f"Patient {pid} missing field: {field}"

    def test_demo_timelines_has_four_patients(self):
        """Test that DEMO_TIMELINES contains timelines for all 4 patients."""
        assert len(DEMO_TIMELINES) == 4
        for pid in ["P1", "P2", "P3", "P4"]:
            assert pid in DEMO_TIMELINES
            assert len(DEMO_TIMELINES[pid]) > 0

    def test_demo_timeline_event_structure(self):
        """Test that each timeline event has the required fields."""
        required_fields = {"ts", "kind", "summary", "details"}
        valid_kinds = {"visit", "flare", "lab", "med_change", "journal"}

        for pid, timeline in DEMO_TIMELINES.items():
            for event in timeline:
                for field in required_fields:
                    assert field in event, f"Patient {pid} event missing field: {field}"
                assert event["kind"] in valid_kinds, f"Patient {pid} has invalid event kind: {event['kind']}"

    def test_get_patient_list(self):
        """Test get_patient_list returns list with id, label, summary."""
        patients = get_patient_list()
        assert len(patients) == 4

        for p in patients:
            assert "id" in p
            assert "label" in p
            assert "summary" in p

    def test_get_patient_returns_patient(self):
        """Test get_patient returns correct patient."""
        patient = get_patient("P1")
        assert patient is not None
        assert patient["id"] == "P1"

    def test_get_patient_returns_none_for_invalid_id(self):
        """Test get_patient returns None for invalid ID."""
        patient = get_patient("INVALID")
        assert patient is None

    def test_get_timeline_returns_events(self):
        """Test get_timeline returns list of events."""
        timeline = get_timeline("P1")
        assert len(timeline) > 0

    def test_get_timeline_respects_max_events(self):
        """Test get_timeline respects max_events parameter."""
        timeline = get_timeline("P1", max_events=5)
        assert len(timeline) <= 5


class TestEoHDemoEndpoints:
    """Tests for the EoH demo API endpoints."""

    def test_list_patients_returns_four(self):
        """Test GET /api/eoh_demo/patients returns 4 patients."""
        response = client.get("/api/eoh_demo/patients")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 4

        ids = [p["id"] for p in data]
        assert "P1" in ids
        assert "P2" in ids
        assert "P3" in ids
        assert "P4" in ids

    def test_get_patient_state_p1(self):
        """Test GET /api/eoh_demo/patient_state/P1 returns expected fields."""
        response = client.get("/api/eoh_demo/patient_state/P1")
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == "P1"
        assert "age" in data
        assert "sex" in data
        assert "diagnosis" in data
        assert "terrain" in data
        assert "serostatus" in data
        assert "current_meds" in data
        assert "recent_flare_history" in data
        assert "recent_das28" in data
        assert "recent_labs" in data
        assert "summary" in data

    def test_get_patient_state_all_patients(self):
        """Test GET /api/eoh_demo/patient_state/{id} works for all patients."""
        for pid in ["P1", "P2", "P3", "P4"]:
            response = client.get(f"/api/eoh_demo/patient_state/{pid}")
            assert response.status_code == 200
            data = response.json()
            assert data["patient_id"] == pid

    def test_get_patient_state_not_found(self):
        """Test GET /api/eoh_demo/patient_state/{id} returns 404 for invalid ID."""
        response = client.get("/api/eoh_demo/patient_state/INVALID")
        assert response.status_code == 404

    def test_get_timeline_p1(self):
        """Test GET /api/eoh_demo/timeline/P1 returns non-empty array."""
        response = client.get("/api/eoh_demo/timeline/P1")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for event in data:
            assert "ts" in event
            assert "kind" in event
            assert "summary" in event
            assert "details" in event

    def test_get_timeline_all_patients(self):
        """Test GET /api/eoh_demo/timeline/{id} works for all patients."""
        for pid in ["P1", "P2", "P3", "P4"]:
            response = client.get(f"/api/eoh_demo/timeline/{pid}")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

    def test_get_timeline_max_events(self):
        """Test GET /api/eoh_demo/timeline/{id}?max_events=5 limits results."""
        response = client.get("/api/eoh_demo/timeline/P1?max_events=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 5

    def test_get_timeline_not_found(self):
        """Test GET /api/eoh_demo/timeline/{id} returns 404 for invalid ID."""
        response = client.get("/api/eoh_demo/timeline/INVALID")
        assert response.status_code == 404

    def test_hypothetical_endpoint(self):
        """Test POST /api/eoh_demo/hypothetical creates hypothetical state."""
        response = client.post(
            "/api/eoh_demo/hypothetical",
            json={
                "base_patient_id": "P1",
                "changes": [
                    {
                        "ts": "2025-09-01T08:00:00Z",
                        "kind": "flare",
                        "severity": "moderate",
                        "summary": "New flare knees/wrists"
                    }
                ]
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == "P1"
        assert data["hypothetical"] is True
        assert "changes_applied" in data
        assert len(data["changes_applied"]) == 1
        assert "[HYPOTHETICAL]" in data["summary"]

    def test_hypothetical_not_found(self):
        """Test POST /api/eoh_demo/hypothetical returns 404 for invalid patient."""
        response = client.post(
            "/api/eoh_demo/hypothetical",
            json={
                "base_patient_id": "INVALID",
                "changes": []
            }
        )
        assert response.status_code == 404

    def test_legacy_patient_state_endpoint(self):
        """Test GET /api/eoh_demo/patient_state (legacy) returns P1 data."""
        response = client.get("/api/eoh_demo/patient_state")
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == "P1"

    def test_legacy_timeline_endpoint(self):
        """Test GET /api/eoh_demo/timeline (legacy) returns P1 timeline."""
        response = client.get("/api/eoh_demo/timeline")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
