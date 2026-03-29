# AUTO-GENERATED TESTS for server/api/auth_routes_postgres.py
import pytest
from unittest import mock

try:
    from server.api import auth_routes_postgres
except ImportError:
    pytest.skip('server.api.auth_routes_postgres not importable', allow_module_level=True)

import types

@pytest.mark.asyncio
async def test_register_user_password_weak(monkeypatch):
    user = mock.Mock()
    user.password = 'weakpw'
    user.email = 'test@example.com'
    background_tasks = mock.Mock()
    session = mock.Mock()
    # Patch validate_password_complexity to return errors
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: ['too short'])
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.register_user(user, background_tasks, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'password_weak' in str(e.value.detail)

@pytest.mark.asyncio
async def test_register_user_email_already_registered(monkeypatch):
    user = mock.Mock()
    user.password = 'StrongPassw0rd!'
    user.email = 'test@example.com'
    background_tasks = mock.Mock()
    session = mock.AsyncMock()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    # Patch session.execute to return an existing user
    result = mock.Mock()
    result.scalar_one_or_none.return_value = object()
    session.execute.return_value = result
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.register_user(user, background_tasks, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Email already registered' in str(e.value.detail)

@pytest.mark.asyncio
async def test_login_for_access_token_bad_credentials(monkeypatch):
    form_data = mock.Mock()
    form_data.username = 'user@example.com'
    form_data.password = 'badpw'
    session = mock.Mock()
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=None))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_access_token(form_data, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'bad_credentials' in str(e.value.detail)

@pytest.mark.asyncio
async def test_login_for_access_token_email_not_verified(monkeypatch):
    form_data = mock.Mock()
    form_data.username = 'user@example.com'
    form_data.password = 'pw'
    session = mock.Mock()
    user = mock.Mock()
    user.is_verified = False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=user))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_access_token(form_data, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'email_not_verified' in str(e.value.detail)

@pytest.mark.asyncio
async def test_login_for_mobile_access_token_bad_credentials(monkeypatch):
    form_data = mock.Mock()
    form_data.username = 'user@example.com'
    form_data.password = 'badpw'
    session = mock.Mock()
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=None))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_mobile_access_token(form_data, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'bad_credentials' in str(e.value.detail)

@pytest.mark.asyncio
async def test_login_for_mobile_access_token_email_not_verified(monkeypatch):
    form_data = mock.Mock()
    form_data.username = 'user@example.com'
    form_data.password = 'pw'
    session = mock.Mock()
    user = mock.Mock()
    user.is_verified = False
    monkeypatch.setattr(auth_routes_postgres, 'authenticate_user', mock.AsyncMock(return_value=user))
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.login_for_mobile_access_token(form_data, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_401_UNAUTHORIZED
    assert 'email_not_verified' in str(e.value.detail)

@pytest.mark.asyncio
async def test_verify_email_invalid_token(monkeypatch):
    session = mock.AsyncMock()
    result = mock.Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.verify_email('badtoken', session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid verification token' in str(e.value.detail)

@pytest.mark.asyncio
async def test_verify_email_token_expired(monkeypatch):
    session = mock.AsyncMock()
    user = mock.Mock()
    import datetime
    user.verification_token_expires = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    result = mock.Mock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.verify_email('token', session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Verification token expired' in str(e.value.detail)

@pytest.mark.asyncio
async def test_forgot_password_email_not_found(monkeypatch):
    body = mock.Mock()
    body.email = 'notfound@example.com'
    background_tasks = mock.Mock()
    session = mock.AsyncMock()
    result = mock.Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    resp = await auth_routes_postgres.forgot_password(body, background_tasks, session)
    assert 'message' in resp
    assert 'password reset link' in resp['message']

@pytest.mark.asyncio
async def test_reset_password_invalid_token(monkeypatch):
    token = 'badtoken'
    body = mock.Mock()
    body.new_password = 'StrongPassw0rd!'
    session = mock.AsyncMock()
    monkeypatch.setattr(auth_routes_postgres, 'validate_password_complexity', lambda pw: [])
    result = mock.Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.reset_password(token, body, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'Invalid reset token' in str(e.value.detail)

@pytest.mark.asyncio
async def test_resend_verification_user_not_found(monkeypatch):
    payload = mock.Mock()
    payload.email = 'notfound@example.com'
    background_tasks = mock.Mock()
    session = mock.AsyncMock()
    result = mock.Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    resp = await auth_routes_postgres.resend_verification(payload, background_tasks, session)
    assert 'detail' in resp
    assert 'verification link' in resp['detail']

@pytest.mark.asyncio
async def test_resend_verification_already_verified(monkeypatch):
    payload = mock.Mock()
    payload.email = 'already@verified.com'
    background_tasks = mock.Mock()
    session = mock.AsyncMock()
    user = mock.Mock()
    user.is_verified = True
    result = mock.Mock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.resend_verification(payload, background_tasks, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_400_BAD_REQUEST
    assert 'already_verified' in str(e.value.detail)

@pytest.mark.asyncio
async def test_get_current_user_info(monkeypatch):
    request = mock.Mock()
    request.url.path = '/api/auth/users/me'
    current_user = mock.Mock()
    current_user.id = 1
    current_user.email = 'user@example.com'
    current_user.full_name = 'User Name'
    current_user.birthdate = '2000-01-01'
    current_user.subscription_tier = 'free'
    current_user.user_type = 'patient'
    current_user.created_at = '2023-01-01T00:00:00Z'
    resp = await auth_routes_postgres.get_current_user_info(request, current_user)
    assert hasattr(resp, 'id')
    assert resp.email == 'user@example.com'

@pytest.mark.asyncio
async def test_accept_doctor_invite_wrong_user_type(monkeypatch):
    body = mock.Mock()
    body.token = 'tok'
    current_user = mock.Mock()
    current_user.user_type = 'doctor'
    session = mock.AsyncMock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.accept_doctor_invite(body, current_user, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only patients' in str(e.value.detail)

@pytest.mark.asyncio
async def test_accept_patient_invite_wrong_user_type(monkeypatch):
    body = mock.Mock()
    body.token = 'tok'
    current_user = mock.Mock()
    current_user.user_type = 'patient'
    session = mock.AsyncMock()
    with pytest.raises(auth_routes_postgres.HTTPException) as e:
        await auth_routes_postgres.accept_patient_invite(body, current_user, session)
    assert e.value.status_code == auth_routes_postgres.status.HTTP_403_FORBIDDEN
    assert 'Only doctors' in str(e.value.detail)
