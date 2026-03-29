import pytest
try:
    import bcrypt
    from server.api import auth_postgres
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
import types
from unittest import mock
from datetime import timedelta, datetime

# verify_password

def test_verify_password_true():
    password = 'secret123'
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    assert auth_postgres.verify_password(password, hashed)

def test_verify_password_false():
    password = 'secret123'
    hashed = bcrypt.hashpw('otherpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    assert not auth_postgres.verify_password(password, hashed)

# get_password_hash

def test_get_password_hash_roundtrip():
    password = 'mypassword!'
    hashed = auth_postgres.get_password_hash(password)
    assert isinstance(hashed, str)
    assert auth_postgres.verify_password(password, hashed)

# get_user_by_email
@pytest.mark.asyncio
def test_get_user_by_email_found(monkeypatch):
    class FakeUser:
        id = 1
        email = 'a@b.com'
        full_name = 'A B'
        hashed_password = 'hash'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'doctor'
        created_at = '2020-01-01'
        last_login = '2021-01-01'
        is_verified = True
        verification_token = 'tok'
        verification_token_expires = '2022-01-01'
    class FakeResult:
        def scalar_one_or_none(self):
            return FakeUser()
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
    monkeypatch.setattr(auth_postgres, 'UserInDB', lambda **kwargs: types.SimpleNamespace(**kwargs))
    user = await auth_postgres.get_user_by_email('a@b.com', FakeDB())
    assert user.email == 'a@b.com'
    assert user.user_type == 'doctor'

@pytest.mark.asyncio
def test_get_user_by_email_not_found(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
    user = await auth_postgres.get_user_by_email('notfound@b.com', FakeDB())
    assert user is None

# authenticate_user
@pytest.mark.asyncio
def test_authenticate_user_success(monkeypatch):
    fake_user = types.SimpleNamespace(email='a@b.com', hashed_password='hash', is_verified=True)
    async def fake_get_user_by_email(email, db):
        return fake_user
    def fake_verify_password(password, hashed):
        return True
    class FakeResult:
        def scalar_one_or_none(self):
            return types.SimpleNamespace()
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    monkeypatch.setattr(auth_postgres, 'verify_password', fake_verify_password)
    user = await auth_postgres.authenticate_user('a@b.com', 'pw', FakeDB())
    assert user is not False

@pytest.mark.asyncio
def test_authenticate_user_fail(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None
    class FakeDB:
        async def execute(self, query):
            return None
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    user = await auth_postgres.authenticate_user('no@b.com', 'pw', FakeDB())
    assert user is False

# create_access_token
def test_create_access_token(monkeypatch):
    monkeypatch.setattr(auth_postgres, 'jwt', mock.Mock())
    monkeypatch.setattr(auth_postgres, 'SECRET_KEY', 'secret')
    monkeypatch.setattr(auth_postgres, 'ALGORITHM', 'HS256')
    monkeypatch.setattr(auth_postgres, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    fake_jwt = mock.Mock()
    auth_postgres.jwt.encode.return_value = 'token123'
    data = {'sub': 'user1'}
    token = auth_postgres.create_access_token(data)
    assert token == 'token123'
    # Test with expires_delta
    token2 = auth_postgres.create_access_token(data, expires_delta=timedelta(minutes=5))
    assert token2 == 'token123'
