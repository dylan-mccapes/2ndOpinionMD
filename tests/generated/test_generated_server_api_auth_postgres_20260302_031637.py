import pytest
from unittest import mock

try:
    from server.api import auth_postgres
except ImportError:
    pytest.skip('server.api.auth_postgres could not be imported', allow_module_level=True)

import bcrypt
import types
import asyncio


def test_verify_password(monkeypatch):
    called = {}
    def fake_checkpw(pw, hashed):
        called['pw'] = pw
        called['hashed'] = hashed
        return True
    monkeypatch.setattr(auth_postgres.bcrypt, 'checkpw', fake_checkpw)
    assert auth_postgres.verify_password('plain', 'hashed') is True
    assert called['pw'] == b'plain'
    assert called['hashed'] == b'hashed'

def test_get_password_hash(monkeypatch):
    def fake_hashpw(pw, salt):
        return b'hashedpw'
    def fake_gensalt():
        return b'salt'
    monkeypatch.setattr(auth_postgres.bcrypt, 'hashpw', fake_hashpw)
    monkeypatch.setattr(auth_postgres.bcrypt, 'gensalt', fake_gensalt)
    result = auth_postgres.get_password_hash('secret')
    assert result == 'hashedpw'

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
    class DummyResult:
        def scalar_one_or_none(self):
            return DummyUser()
    class DummySession:
        async def execute(self, query):
            return DummyResult()
    user = await auth_postgres.get_user_by_email('a@b.com', DummySession())
    assert user.email == 'a@b.com'
    assert user.user_type == 'patient'

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(monkeypatch):
    class DummyResult:
        def scalar_one_or_none(self):
            return None
    class DummySession:
        async def execute(self, query):
            return DummyResult()
    user = await auth_postgres.get_user_by_email('none@b.com', DummySession())
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch):
    class DummyUser:
        hashed_password = 'hpw'
        email = 'a@b.com'
    async def fake_get_user_by_email(email, db):
        return DummyUser()
    def fake_verify_password(password, hashed):
        return True
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    monkeypatch.setattr(auth_postgres, 'verify_password', fake_verify_password)
    # Patch select/User/commit chain
    class DummyResult:
        def scalar_one_or_none(self):
            class DummyDBUser:
                failed_login_attempts = 0
                locked_until = None
            return DummyDBUser()
    class DummySession:
        async def execute(self, query):
            return DummyResult()
        async def commit(self):
            pass
    user = await auth_postgres.authenticate_user('a@b.com', 'pw', DummySession())
    assert user is not None

@pytest.mark.asyncio
async def test_authenticate_user_fail(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    user = await auth_postgres.authenticate_user('a@b.com', 'pw', None)
    assert user is False

def test_create_access_token(monkeypatch):
    called = {}
    def fake_jwt_encode(data, key, algorithm):
        called['data'] = data
        called['key'] = key
        called['algorithm'] = algorithm
        return 'token123'
    monkeypatch.setattr(auth_postgres.jwt, 'encode', fake_jwt_encode)
    monkeypatch.setattr(auth_postgres, 'SECRET_KEY', 'sk')
    monkeypatch.setattr(auth_postgres, 'ALGORITHM', 'HS256')
    monkeypatch.setattr(auth_postgres, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    from datetime import timedelta
    token = auth_postgres.create_access_token({'foo': 'bar'}, timedelta(minutes=1))
    assert token == 'token123'
    assert 'exp' in called['data'] or 'exp' in token
