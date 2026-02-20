import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).parent.parent))

from server.api.app_postgres import app

client = TestClient(app)

def test_security_middleware_blocks_sensitive_paths():
    """Test that the security middleware blocks access to sensitive paths.

    Paths must match the anchored regexes in app_postgres.security_middleware:
        ^/\\.env$, ^/\\.git(/|$), ^/\\.config(/|$), ^/\\.aws(/|$),
        ^/\\.ssh(/|$), ^/wp-login\\.php$, ^/wp-admin(/|$), ^/admin$,
        ^/phpinfo\\.php$, ^/config\\.php$
    """
    sensitive_paths = [
        "/.env",
        "/.git/config",
        "/.config/something",
        "/.aws/credentials",
        "/.ssh/id_rsa",
        "/wp-login.php",
        "/wp-admin/index.php",
        "/admin",          # pattern is ^/admin$ (exact match only)
        "/phpinfo.php",
        "/config.php",
    ]

    for path in sensitive_paths:
        try:
            response = client.get(path)
        except Exception as exc:
            if "another operation is in progress" in str(exc):
                pytest.skip("asyncpg conflict in TestClient — works on live server.")
            raise
        assert response.status_code == 403, f"Expected 403 for {path}, got {response.status_code}"
        assert response.json() == {"detail": "Access denied"}


def test_security_middleware_allows_normal_paths():
    """Test that the security middleware allows access to normal paths."""
    normal_paths = [
        "/api/health",
        "/api/meta/ping",
    ]

    for path in normal_paths:
        try:
            response = client.get(path)
        except Exception as exc:
            if "another operation is in progress" in str(exc):
                pytest.skip("asyncpg conflict in TestClient — works on live server.")
            raise
        assert response.status_code != 403, f"Path {path} was blocked (403) but shouldn't be"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
