try:
    import pytest
    from unittest import mock
    from server.api import auth_routes_postgres
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_register_user_password_weak(monkeypatch):
    class DummyUser:
        password = '123'
        email = 'test@example.com'
    class DummySession:
        async def execute(self, query):
            class Result:
                def scalar_one_or_none(self):
                    return None
            return Result()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: ['too short'])
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.register_user(DummyUser(), mock.Mock(), DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert e.value.detail['code'] == 'password_weak'

@pytest.mark.asyncio
def test_login_for_access_token_bad_credentials(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'badpass'
    class DummySession:
        pass
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=None))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.login_for_access_token(DummyForm(), DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert e.value.detail['code'] == 'bad_credentials'

@pytest.mark.asyncio
def test_login_for_mobile_access_token_email_not_verified(monkeypatch):
    class DummyForm:
        username = 'user'
        password = 'pass'
    class DummyUser:
        is_verified = False
    class DummySession:
        pass
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=DummyUser()))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.login_for_mobile_access_token(DummyForm(), DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert e.value.detail['code'] == 'email_not_verified'

@pytest.mark.asyncio
def test_verify_email_invalid_token(monkeypatch):
    class DummySession:
        async def execute(self, query):
            class Result:
                def scalar_one_or_none(self):
                    return None
            return Result()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.verify_email('badtoken', DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid verification token' in str(e.value.detail)

@pytest.mark.asyncio
def test_forgot_password_email_not_found(monkeypatch):
    class DummyBody:
        email = 'notfound@example.com'
    class DummySession:
        async def execute(self, query):
            class Result:
                def scalar_one_or_none(self):
                    return None
            return Result()
    result = None
    async def run():
        nonlocal result
        result = await auth_routes_postgres.forgot_password(DummyBody(), mock.Mock(), DummySession())
    import asyncio
    asyncio.run(run())
    assert 'message' in result
    assert 'password reset link' in result['message']

@pytest.mark.asyncio
def test_reset_password_invalid_token(monkeypatch):
    class DummyBody:
        new_password = 'StrongPassw0rd!'
    class DummySession:
        async def execute(self, query):
            class Result:
                def scalar_one_or_none(self):
                    return None
            return Result()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.reset_password('badtoken', DummyBody(), DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid reset token' in str(e.value.detail)

@pytest.mark.asyncio
def test_resend_verification_already_verified(monkeypatch):
    class DummyPayload:
        email = 'verified@example.com'
    class DummyUser:
        is_verified = True
    class DummySession:
        async def execute(self, query):
            class Result:
                def scalar_one_or_none(self):
                    return DummyUser()
            return Result()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.resend_verification(DummyPayload(), mock.Mock(), DummySession()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert e.value.detail['code'] == 'already_verified'

@pytest.mark.asyncio
def test_get_current_user_info_patient(monkeypatch):
    class DummyRequest:
        class DummyURL:
            path = '/api/auth/users/me'
        url = DummyURL()
    class DummyUser:
        id = 1
        email = 'pat@example.com'
        full_name = 'Pat Example'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = None
        created_at = '2020-01-01'
    monkeypatch.setattr(auth_routes_postgres, 'UserResponse', lambda **kwargs: kwargs)
    result = None
    async def run():
        nonlocal result
        result = await auth_routes_postgres.get_current_user_info(DummyRequest(), DummyUser())
    import asyncio
    asyncio.run(run())
    assert result['email'] == 'pat@example.com'
    assert result['user_type'] == 'patient'

@pytest.mark.asyncio
def test_accept_doctor_invite_wrong_user_type(monkeypatch):
    class DummyBody:
        token = 'tok'
    class DummyUser:
        user_type = 'doctor'
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.accept_doctor_invite(DummyBody(), DummyUser(), mock.Mock()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only patients' in str(e.value.detail)

@pytest.mark.asyncio
def test_accept_patient_invite_wrong_user_type(monkeypatch):
    class DummyBody:
        token = 'tok'
    class DummyUser:
        user_type = 'patient'
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        import asyncio
        asyncio.run(auth_routes_postgres.accept_patient_invite(DummyBody(), DummyUser(), mock.Mock()))
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only doctors' in str(e.value.detail)
