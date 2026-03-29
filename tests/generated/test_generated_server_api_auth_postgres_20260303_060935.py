try:
    import pytest
    from server.api import auth_postgres
    from unittest.mock import patch, AsyncMock, MagicMock
    import bcrypt
    import jwt
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_verify_password_true(monkeypatch):
    monkeypatch.setattr(auth_postgres.bcrypt, 'checkpw', lambda p, h: True)
    assert auth_postgres.verify_password('plain', 'hashed') is True

def test_verify_password_false(monkeypatch):
    monkeypatch.setattr(auth_postgres.bcrypt, 'checkpw', lambda p, h: False)
    assert auth_postgres.verify_password('plain', 'hashed') is False

def test_get_password_hash(monkeypatch):
    fake_hash = b'hashedpw'
    monkeypatch.setattr(auth_postgres.bcrypt, 'hashpw', lambda p, s: fake_hash)
    monkeypatch.setattr(auth_postgres.bcrypt, 'gensalt', lambda: b'salt')
    result = auth_postgres.get_password_hash('password')
    assert isinstance(result, str)
    assert 'hashedpw' in result

@pytest.mark.asyncio
async def test_get_user_by_email_found(monkeypatch):
    class DummyUser:
        id = 1
        email = 'a@b.com'
        full_name = 'A B'
        hashed_password = 'hpw'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'patient'
        created_at = 'now'
        last_login = 'now'
        is_verified = True
        verification_token = None
        verification_token_expires = None
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = DummyUser()
    dummy_db = MagicMock()
    dummy_db.execute = AsyncMock(return_value=dummy_result)
    user = await auth_postgres.get_user_by_email('a@b.com', dummy_db)
    assert user.email == 'a@b.com'
    assert user.user_type == 'patient'

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(monkeypatch):
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = None
    dummy_db = MagicMock()
    dummy_db.execute = AsyncMock(return_value=dummy_result)
    user = await auth_postgres.get_user_by_email('notfound@b.com', dummy_db)
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch):
    fake_user = MagicMock()
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', AsyncMock(return_value=fake_user))
    monkeypatch.setattr(auth_postgres, 'verify_password', lambda p, h: True)
    dummy_db = MagicMock()
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = fake_user
    dummy_db.execute = AsyncMock(return_value=dummy_result)
    user = await auth_postgres.authenticate_user('a@b.com', 'pw', dummy_db)
    assert user == fake_user

@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(monkeypatch):
    fake_user = MagicMock()
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', AsyncMock(return_value=fake_user))
    monkeypatch.setattr(auth_postgres, 'verify_password', lambda p, h: False)
    dummy_db = MagicMock()
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = fake_user
    dummy_db.execute = AsyncMock(return_value=dummy_result)
    dummy_db.commit = AsyncMock()
    user = await auth_postgres.authenticate_user('a@b.com', 'badpw', dummy_db)
    assert user is False

@pytest.mark.asyncio
async def test_authenticate_user_not_found(monkeypatch):
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', AsyncMock(return_value=None))
    dummy_db = MagicMock()
    user = await auth_postgres.authenticate_user('notfound@b.com', 'pw', dummy_db)
    assert user is False

def test_create_access_token(monkeypatch):
    monkeypatch.setattr(auth_postgres, 'jwt', MagicMock())
    monkeypatch.setattr(auth_postgres, 'SECRET_KEY', 'secret')
    monkeypatch.setattr(auth_postgres, 'ALGORITHM', 'HS256')
    monkeypatch.setattr(auth_postgres, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    data = {'sub': 'user'}
    auth_postgres.jwt.encode.return_value = 'token'
    token = auth_postgres.create_access_token(data)
    assert token == 'token'
