try:
    import pytest
    from unittest import mock
    from server.api import auth_routes_postgres
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

# register_user
@pytest.mark.asyncio
async def test_register_user_password_weak(monkeypatch):
    class UserCreate:
        email = 'a@b.com'
        password = 'pw'
    class FakeSession:
        async def execute(self, q):
            class R: def scalar_one_or_none(self): return None
            return R()
    def fake_validate_password_complexity(pw):
        return ['too short']
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', fake_validate_password_complexity)
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.register_user(UserCreate(), mock.Mock(), FakeSession())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'password_weak' in str(e.value.detail)

@pytest.mark.asyncio
async def test_register_user_email_exists(monkeypatch):
    class UserCreate:
        email = 'a@b.com'
        password = 'pw'
    class FakeSession:
        async def execute(self, q):
            class R: def scalar_one_or_none(self): return object()
            return R()
    def fake_validate_password_complexity(pw):
        return []
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', fake_validate_password_complexity)
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.register_user(UserCreate(), mock.Mock(), FakeSession())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'already registered' in str(e.value.detail)

# login_for_access_token
@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch):
    class Form:
        username = 'a@b.com'
        password = 'pw'
    async def fake_authenticate_user(email, pw, session):
        return False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', fake_authenticate_user)
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_access_token(Form(), mock.Mock())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'bad_credentials' in str(e.value.detail)

@pytest.mark.asyncio
async def test_login_for_access_token_email_not_verified(monkeypatch):
    class Form:
        username = 'a@b.com'
        password = 'pw'
    class User:
        is_verified = False
    async def fake_authenticate_user(email, pw, session):
        return User()
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', fake_authenticate_user)
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_access_token(Form(), mock.Mock())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'email_not_verified' in str(e.value.detail)

# login_for_mobile_access_token
@pytest.mark.asyncio
async def test_login_for_mobile_access_token_bad_credentials(monkeypatch):
    class Form:
        username = 'a@b.com'
        password = 'pw'
    async def fake_authenticate_user(email, pw, session):
        return False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', fake_authenticate_user)
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_mobile_access_token(Form(), mock.Mock())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'bad_credentials' in str(e.value.detail)

# verify_email
@pytest.mark.asyncio
async def test_verify_email_invalid_token(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeSession:
        async def execute(self, q):
            return FakeResult()
    monkeypatch.setattr(auth_routes_postgres, 'User', type('User', (), {}))
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda x: 'query')
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.verify_email('badtoken', FakeSession())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid verification token' in str(e.value.detail)

# forgot_password
@pytest.mark.asyncio
async def test_forgot_password_email_not_found(monkeypatch):
    class Body:
        email = 'a@b.com'
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeSession:
        async def execute(self, q):
            return FakeResult()
        async def commit(self):
            pass
    result = await auth_routes_postgres.forgot_password(Body(), mock.Mock(), FakeSession())
    assert 'message' in result

# reset_password
@pytest.mark.asyncio
async def test_reset_password_invalid_token(monkeypatch):
    class Body:
        new_password = 'pw'
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeSession:
        async def execute(self, q):
            return FakeResult()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    monkeypatch.setattr(auth_routes_postgres, 'User', type('User', (), {}))
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda x: 'query')
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.reset_password('badtoken', Body(), FakeSession())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid reset token' in str(e.value.detail)

# resend_verification
@pytest.mark.asyncio
async def test_resend_verification_user_not_found(monkeypatch):
    class Payload:
        email = 'a@b.com'
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeSession:
        async def execute(self, q):
            return FakeResult()
    result = await auth_routes_postgres.resend_verification(Payload(), mock.Mock(), FakeSession())
    assert 'detail' in result

# get_current_user_info
@pytest.mark.asyncio
async def test_get_current_user_info(monkeypatch):
    class Request:
        class URL:
            path = '/api/auth/users/me'
        url = URL()
    class User:
        id = 1
        email = 'a@b.com'
        full_name = 'A B'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'doctor'
        created_at = 'now'
    monkeypatch.setattr(auth_routes_postgres, 'UserResponse', lambda **kwargs: kwargs)
    result = await auth_routes_postgres.get_current_user_info(Request(), User())
    assert result['email'] == 'a@b.com'
    assert result['user_type'] == 'doctor'

# accept_doctor_invite
@pytest.mark.asyncio
async def test_accept_doctor_invite_wrong_user_type(monkeypatch):
    class Body:
        token = 'tok'
    class User:
        user_type = 'doctor'
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.accept_doctor_invite(Body(), User(), mock.Mock())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only patients' in str(e.value.detail)

# accept_patient_invite
@pytest.mark.asyncio
async def test_accept_patient_invite_wrong_user_type(monkeypatch):
    class Body:
        token = 'tok'
    class User:
        user_type = 'patient'
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.accept_patient_invite(Body(), User(), mock.Mock())
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only doctors' in str(e.value.detail)
