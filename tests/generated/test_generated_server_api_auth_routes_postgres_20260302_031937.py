import pytest
import sys
from unittest import mock

pytestmark = pytest.mark.asyncio

try:
    from server.api import auth_routes_postgres
except ImportError:
    pytest.skip('server.api.auth_routes_postgres not importable', allow_module_level=True)

# Helper for async mocks
class AsyncMock(mock.MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

@pytest.fixture
def fake_session():
    session = mock.MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def fake_background_tasks():
    return mock.MagicMock()

@pytest.fixture
def fake_user():
    class User:
        id = 1
        email = 'test@example.com'
        full_name = 'Test User'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'patient'
        created_at = '2023-01-01T00:00:00Z'
        is_verified = True
        verification_token = None
        verification_token_expires = None
        password_reset_token = None
        password_reset_token_expires = None
    return User()

@pytest.fixture
def fake_user_create():
    class UserCreate:
        email = 'test@example.com'
        password = 'StrongPass123!'
    return UserCreate()

@pytest.fixture
def fake_request():
    class Request:
        url = type('url', (), {'path': '/api/auth/users/me'})
    return Request()

@pytest.mark.asyncio
async def test_register_user_success(monkeypatch, fake_user_create, fake_background_tasks, fake_session):
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'User', object)
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    # Should not raise
    try:
        await auth_routes_postgres.register_user(fake_user_create, fake_background_tasks, fake_session)
    except Exception as e:
        pytest.fail(f'Unexpected exception: {e}')

@pytest.mark.asyncio
async def test_register_user_password_weak(monkeypatch, fake_user_create, fake_background_tasks, fake_session):
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: ['too short'])
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.register_user(fake_user_create, fake_background_tasks, fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert exc.value.detail['code'] == 'password_weak'

@pytest.mark.asyncio
async def test_login_for_access_token_success(monkeypatch, fake_session, fake_user):
    class Form:
        username = 'test@example.com'
        password = 'pw'
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', AsyncMock(return_value=fake_user))
    form = Form()
    # Should not raise
    await auth_routes_postgres.login_for_access_token(form, fake_session)

@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch, fake_session):
    class Form:
        username = 'test@example.com'
        password = 'pw'
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', AsyncMock(return_value=None))
    form = Form()
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.login_for_access_token(form, fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_login_for_access_token_email_not_verified(monkeypatch, fake_session, fake_user):
    class Form:
        username = 'test@example.com'
        password = 'pw'
    fake_user.is_verified = False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', AsyncMock(return_value=fake_user))
    form = Form()
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.login_for_access_token(form, fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail['code'] == 'email_not_verified'

@pytest.mark.asyncio
async def test_login_for_mobile_access_token_success(monkeypatch, fake_session, fake_user):
    class Form:
        username = 'test@example.com'
        password = 'pw'
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', AsyncMock(return_value=fake_user))
    form = Form()
    await auth_routes_postgres.login_for_mobile_access_token(form, fake_session)

@pytest.mark.asyncio
async def test_verify_email_success(monkeypatch, fake_session, fake_user):
    fake_user.verification_token_expires = auth_routes_postgres.datetime.utcnow() + auth_routes_postgres.timedelta(minutes=10)
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = fake_user
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    monkeypatch.setattr(auth_routes_postgres, 'User', object)
    res = await auth_routes_postgres.verify_email('sometoken', fake_session)
    assert 'Email verified successfully' in res['message']

@pytest.mark.asyncio
async def test_verify_email_invalid_token(monkeypatch, fake_session):
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.verify_email('badtoken', fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_forgot_password_user_not_found(monkeypatch, fake_session, fake_background_tasks):
    class ForgotPasswordRequest:
        email = 'notfound@example.com'
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    res = await auth_routes_postgres.forgot_password(ForgotPasswordRequest(), fake_background_tasks, fake_session)
    assert 'password reset link' in res['message']

@pytest.mark.asyncio
async def test_reset_password_invalid_token(monkeypatch, fake_session):
    class ResetPasswordRequest:
        new_password = 'StrongPass123!'
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.reset_password('badtoken', ResetPasswordRequest(), fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_resend_verification_user_not_found(monkeypatch, fake_session, fake_background_tasks):
    class ResendRequest:
        email = 'notfound@example.com'
    fake_result = mock.MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(auth_routes_postgres, 'select', lambda *a, **k: None)
    res = await auth_routes_postgres.resend_verification(ResendRequest(), fake_background_tasks, fake_session)
    assert 'verification link' in res['detail']

@pytest.mark.asyncio
async def test_get_current_user_info_success(fake_request, fake_user):
    res = auth_routes_postgres.get_current_user_info(fake_request, fake_user)
    assert res.email == fake_user.email
    assert res.user_type == 'patient'

@pytest.mark.asyncio
async def test_accept_doctor_invite_wrong_user_type(monkeypatch, fake_user, fake_session):
    class AcceptInviteRequest:
        token = 'tok'
    fake_user.user_type = 'doctor'
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.accept_doctor_invite(AcceptInviteRequest(), fake_user, fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_accept_patient_invite_wrong_user_type(monkeypatch, fake_user, fake_session):
    class AcceptInviteRequest:
        token = 'tok'
    fake_user.user_type = 'patient'
    with pytest.raises(auth_routes_postgres.HTTPException) as exc:
        await auth_routes_postgres.accept_patient_invite(AcceptInviteRequest(), fake_user, fake_session)
    assert exc.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
