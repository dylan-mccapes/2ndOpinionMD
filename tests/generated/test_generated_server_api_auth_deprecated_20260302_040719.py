try:
    import pytest
    from server.api import auth_deprecated
    from fastapi import HTTPException
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_login_for_access_token_raises(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return False
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    class DummySession: pass
    form = DummyForm()
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.login_for_access_token(form, None, DummySession()))
    assert excinfo.value.status_code == 401

@pytest.mark.asyncio
def test_login_for_access_token_locked(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    async def fake_authenticate_user(username, password, session):
        return "locked"
    monkeypatch.setattr(auth_deprecated, 'authenticate_user', fake_authenticate_user)
    class DummySession: pass
    form = DummyForm()
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.login_for_access_token(form, None, DummySession()))
    assert excinfo.value.status_code == 423

@pytest.mark.asyncio
def test_login_for_mobile_access_token_raises():
    class DummyForm: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.login_for_mobile_access_token(DummyForm(), None))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_register_user_raises():
    class DummyUser: pass
    class DummyRequest: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.register_user(DummyUser(), DummyRequest(), None))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_read_users_me_raises():
    class DummyUser: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.read_users_me(DummyUser(), None))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_verify_email_raises():
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.verify_email('sometoken'))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_resend_verification_raises():
    class DummyRequest: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.resend_verification('test@example.com', DummyRequest(), None))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_forgot_password_raises():
    class DummyRequestData: pass
    class DummyRequest: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.forgot_password(DummyRequestData(), DummyRequest(), None))
    assert excinfo.value.status_code == 501

@pytest.mark.asyncio
def test_reset_password_raises():
    class DummyRequestData: pass
    with pytest.raises(HTTPException) as excinfo:
        import asyncio
        asyncio.run(auth_deprecated.reset_password(DummyRequestData(), None))
    assert excinfo.value.status_code == 501
