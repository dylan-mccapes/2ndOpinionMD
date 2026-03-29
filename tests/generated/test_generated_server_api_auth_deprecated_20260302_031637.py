import pytest
from unittest import mock

try:
    from server.api import auth_deprecated
    from fastapi import HTTPException
except ImportError:
    pytest.skip('server.api.auth_deprecated could not be imported', allow_module_level=True)

import asyncio

@pytest.mark.asyncio
async def test_login_for_access_token_locked(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return 'locked'
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_access_token(DummyForm(), None, None)
    assert exc.value.status_code == 423
    assert 'locked' in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return None
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_access_token(DummyForm(), None, None)
    assert exc.value.status_code == 401
    assert 'Incorrect email or password' in exc.value.detail

@pytest.mark.asyncio
async def test_login_for_mobile_access_token():
    class DummyForm:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.login_for_mobile_access_token(DummyForm(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_register_user():
    class DummyUser:
        pass
    class DummyRequest:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.register_user(DummyUser(), DummyRequest(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_read_users_me():
    class DummyUser:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.read_users_me(DummyUser(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_verify_email():
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.verify_email('sometoken')
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_resend_verification():
    class DummyRequest:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.resend_verification('test@example.com', DummyRequest(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_forgot_password():
    class DummyRequest:
        pass
    class DummyForgot:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.forgot_password(DummyForgot(), DummyRequest(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail

@pytest.mark.asyncio
async def test_reset_password():
    class DummyReset:
        pass
    with pytest.raises(HTTPException) as exc:
        await auth_deprecated.reset_password(DummyReset(), None)
    assert exc.value.status_code == 501
    assert 'deprecated' in exc.value.detail
