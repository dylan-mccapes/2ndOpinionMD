try:
    import pytest
    from unittest import mock
    from server.api import auth_routes_postgres
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_register_user_password_weak(monkeypatch):
    class DummyUser:
        password = 'weak'
        email = 'test@example.com'
    async def dummy_execute(query):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: ['too weak'])
    monkeypatch.setattr(auth_routes_postgres, 'get_session', lambda: None)
    session = mock.Mock()
    session.execute = dummy_execute
    user = DummyUser()
    background_tasks = mock.Mock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.register_user(user, background_tasks, session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
def test_login_for_access_token_bad_credentials(monkeypatch):
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=None))
    form_data = mock.Mock(username='user', password='pw')
    session = mock.Mock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.login_for_access_token(form_data, session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
def test_login_for_mobile_access_token_email_not_verified(monkeypatch):
    class DummyUser:
        is_verified = False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=DummyUser()))
    form_data = mock.Mock(username='user', password='pw')
    session = mock.Mock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.login_for_mobile_access_token(form_data, session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
def test_verify_email_invalid_token(monkeypatch):
    session = mock.Mock()
    async def dummy_execute(query):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    session.execute = dummy_execute
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.verify_email('badtoken', session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
def test_forgot_password_email_not_found(monkeypatch):
    class DummyBody:
        email = 'notfound@example.com'
    session = mock.Mock()
    async def dummy_execute(query):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    session.execute = dummy_execute
    background_tasks = mock.Mock()
    result = None
    import asyncio
    result = asyncio.run(auth_routes_postgres.forgot_password(DummyBody(), background_tasks, session))
    assert 'message' in result

@pytest.mark.asyncio
def test_reset_password_invalid_token(monkeypatch):
    class DummyBody:
        new_password = 'StrongPass123!'
    session = mock.Mock()
    async def dummy_execute(query):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    session.execute = dummy_execute
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.reset_password('badtoken', DummyBody(), session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
def test_resend_verification_user_not_found(monkeypatch):
    class DummyPayload:
        email = 'notfound@example.com'
    session = mock.Mock()
    async def dummy_execute(query):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    session.execute = dummy_execute
    background_tasks = mock.Mock()
    import asyncio
    result = asyncio.run(auth_routes_postgres.resend_verification(DummyPayload(), background_tasks, session))
    assert 'detail' in result

@pytest.mark.asyncio
def test_get_current_user_info(monkeypatch):
    class DummyRequest:
        class DummyURL:
            path = '/api/auth/users/me'
        url = DummyURL()
    class DummyUser:
        id = 1
        email = 'a@b.com'
        full_name = 'A B'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'patient'
        created_at = '2020-01-01'
    monkeypatch.setattr(auth_routes_postgres, 'UserResponse', lambda **kwargs: kwargs)
    result = None
    import asyncio
    result = asyncio.run(auth_routes_postgres.get_current_user_info(DummyRequest(), DummyUser()))
    assert result['email'] == 'a@b.com'

@pytest.mark.asyncio
def test_accept_doctor_invite_wrong_user_type(monkeypatch):
    class DummyBody:
        token = 'tok'
    class DummyUser:
        user_type = 'doctor'
    session = mock.Mock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.accept_doctor_invite(DummyBody(), DummyUser(), session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
def test_accept_patient_invite_wrong_user_type(monkeypatch):
    class DummyBody:
        token = 'tok'
    class DummyUser:
        user_type = 'patient'
    session = mock.Mock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.accept_patient_invite(DummyBody(), DummyUser(), session))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
