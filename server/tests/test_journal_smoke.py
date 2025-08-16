import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from server.api.app_postgres import app
from server.api.auth_postgres import get_current_user_postgres
from database.models.postgresql.models import User

def get_mock_user():
    mock_user = Mock(spec=User)
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
    return mock_user

app.dependency_overrides[get_current_user_postgres] = get_mock_user

client = TestClient(app)

class TestJournalEndpoints:
    """Smoke tests for journal endpoints"""
    
    def test_journal_list_no_slash(self):
        """Test GET /api/journal returns 200"""
        response = client.get("/api/journal")
        assert response.status_code == 200
        
    def test_journal_list_with_slash(self):
        """Test GET /api/journal/ returns 200 (no redirect)"""
        response = client.get("/api/journal/")
        assert response.status_code == 200
        
    def test_journal_create_no_slash(self):
        """Test POST /api/journal returns 201"""
        journal_data = {
            "symptoms": [{"symptom": "headache", "severity": 5}],
            "environmental_factors": [],
            "stress_level": 3,
            "notes": "Test entry"
        }
        response = client.post("/api/journal", json=journal_data)
        assert response.status_code == 201
        
    def test_journal_create_with_slash(self):
        """Test POST /api/journal/ returns 201 (no redirect)"""
        journal_data = {
            "symptoms": [{"symptom": "fatigue", "severity": 7}],
            "environmental_factors": [],
            "stress_level": 4,
            "notes": "Another test entry"
        }
        response = client.post("/api/journal/", json=journal_data)
        assert response.status_code == 201
        
    def test_journal_unauthorized(self):
        """Test endpoints return 401 without auth"""
        app.dependency_overrides.clear()
        
        response = client.get("/api/journal")
        assert response.status_code == 401
        
        response = client.post("/api/journal", json={"symptoms": []})
        assert response.status_code == 401
        
        app.dependency_overrides[get_current_user_postgres] = get_mock_user

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
