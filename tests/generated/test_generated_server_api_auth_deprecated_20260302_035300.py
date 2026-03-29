try:
    import pytest
    from server.api import auth_deprecated
    from fastapi import HTTPException
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

import sys

@pytest.mark.asyncio
async def test_login_for_access_token_locked(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return "locked"
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    class DummySession: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_access_token(DummyForm(), None, DummySession())
    assert exc.value.status_code == 423
    assert "locked" in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return None
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    class DummySession: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_access_token(DummyForm(), None, DummySession())
    assert exc.value.status_code == 401
    assert "Incorrect email or password" in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_mobile_access_token_always_raises():
    class DummyForm: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_mobile_access_token(DummyForm(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_register_user_always_raises():
    class DummyUser: pass
    class DummyRequest: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.register_user(DummyUser(), DummyRequest(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_read_users_me_always_raises():
    class DummyUser: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.read_users_me(DummyUser(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_verify_email_always_raises():
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.verify_email("sometoken")
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_resend_verification_always_raises():
    class DummyRequest: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.resend_verification("email@example.com", DummyRequest(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_forgot_password_always_raises():
    class DummyRequest: pass
    class DummyData: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.forgot_password(DummyData(), DummyRequest(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail

@pytest.mark.asyncio
async def test_reset_password_always_raises():
    class DummyData: pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.reset_password(DummyData(), None)
    assert exc.value.status_code == 501
    assert "deprecated" in exc.value.detail
