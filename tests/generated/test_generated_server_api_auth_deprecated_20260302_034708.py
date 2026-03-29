# AUTO-GENERATED TESTS FOR server/api/auth_deprecated.py
import pytest
try:
    from server.api import auth_deprecated
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_login_for_access_token_locked(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    # Patch authenticate_user to return 'locked'
    monkeypatch.setattr(auth_deprecated, "authenticate_user", AsyncMock(return_value="locked"))
    form_data = MagicMock(username="user", password="pass")
    session = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.login_for_access_token(form_data, None, session)
    assert exc.value.status_code == auth_deprecated.status.HTTP_423_LOCKED
    assert "locked" in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    # Patch authenticate_user to return False
    monkeypatch.setattr(auth_deprecated, "authenticate_user", AsyncMock(return_value=False))
    form_data = MagicMock(username="user", password="pass")
    session = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.login_for_access_token(form_data, None, session)
    assert exc.value.status_code == auth_deprecated.status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_mobile_access_token_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    form_data = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.login_for_mobile_access_token(form_data, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_register_user_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    user = MagicMock()
    request = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.register_user(user, request, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_read_users_me_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    current_user = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.read_users_me(current_user, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_verify_email_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.verify_email("sometoken")
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_resend_verification_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    email = "test@example.com"
    request = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.resend_verification(email, request, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_forgot_password_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    request_data = MagicMock()
    request = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.forgot_password(request_data, request, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_reset_password_always_raises():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    request_data = MagicMock()
    with pytest.raises(auth_deprecated.HTTPException) as exc:
        await auth_deprecated.reset_password(request_data, None)
    assert exc.value.status_code == auth_deprecated.status.HTTP_501_NOT_IMPLEMENTED
    assert "deprecated" in exc.value.detail
