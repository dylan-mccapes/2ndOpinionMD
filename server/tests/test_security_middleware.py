import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).parent.parent))

from api.app import app

client = TestClient(app)

def test_security_middleware_blocks_sensitive_paths():
    """Test that the security middleware blocks access to sensitive paths"""
    sensitive_paths = [
        "/.env",
        "/.git/config",
        "/.config/something",
        "/.aws/credentials",
        "/.ssh/id_rsa",
        "/wp-login.php",
        "/wp-admin/index.php",
        "/admin/login",
        "/phpinfo.php",
        "/config.php",
    ]
    
    for path in sensitive_paths:
        response = client.get(path)
        assert response.status_code == 403
        assert response.json() == {"detail": "Access denied"}
        
def test_security_middleware_allows_normal_paths():
    """Test that the security middleware allows access to normal paths"""
    normal_paths = [
        "/api/health",
        "/api/auth/token",
        "/api/journal",
    ]
    
    for path in normal_paths:
        response = client.get(path)
        assert response.status_code != 403

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
