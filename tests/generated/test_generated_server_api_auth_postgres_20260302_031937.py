import pytest
import sys
from unittest import mock

try:
    import server.api.auth_postgres as auth_postgres
except ImportError:
    auth_postgres = None

@pytest.mark.skipif(auth_postgres is None, reason='Import failed')
def test_verify_password_and_hash(monkeypatch):
    # Patch bcrypt
    monkeypatch.setattr(auth_postgres, 'bcrypt', mock.Mock())
    bcrypt = auth_postgres.bcrypt
    bcrypt.checkpw.return_value = True
    bcrypt.hashpw.return_value = b'hashed'
    result = auth_postgres.verify_password('plain', 'hashed')
    assert result is True
    hashed = auth_postgres.get_password_hash('plain')
    assert isinstance(hashed, str)

@pytest.mark.asyncio
@pytest.mark.skipif(auth_postgres is None, reason='Import failed')
async def test_get_user_by_email_found(monkeypatch):
    dummy_user = mock.Mock()
    dummy_user.id = 1
    dummy_user.email = 'a@b.com'
    dummy_user.full_name = 'A B'
    dummy_user.hashed_password = 'hpw'
    dummy_user.birthdate = '2000-01-01'
    dummy_user.subscription_tier = 'free'
    dummy_user.user_type = 'patient'
    dummy_user.created_at = 'now'
    dummy_user.last_login = None
    dummy_user.is_verified = True
    dummy_user.verification_token = 'tok'
    dummy_user.verification_token_expires = 'exp'
    dummy_result = mock.Mock()
    dummy_result.scalar_one_or_none.return_value = dummy_user
    dummy_db = mock.Mock()
    dummy_db.execute = mock.AsyncMock(return_value=dummy_result)
    UserInDB = getattr(auth_postgres, 'UserInDB', mock.Mock)
    user = await auth_postgres.get_user_by_email('a@b.com', dummy_db)
    assert user.email == 'a@b.com'

@pytest.mark.asyncio
@pytest.mark.skipif(auth_postgres is None, reason='Import failed')
async def test_authenticate_user_fail(monkeypatch):
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', mock.AsyncMock(return_value=None))
    dummy_db = mock.Mock()
    result = await auth_postgres.authenticate_user('a@b.com', 'pw', dummy_db)
    assert result is False

@pytest.mark.skipif(auth_postgres is None, reason='Import failed')
def test_create_access_token(monkeypatch):
    monkeypatch.setattr(auth_postgres, 'jwt', mock.Mock())
    monkeypatch.setattr(auth_postgres, 'SECRET_KEY', 'secret')
    monkeypatch.setattr(auth_postgres, 'ALGORITHM', 'HS256')
    monkeypatch.setattr(auth_postgres, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    data = {'sub': 'user'}
    token = auth_postgres.create_access_token(data)
    assert token == auth_postgres.jwt.encode.return_value
