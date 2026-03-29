try:
    import pytest
    from unittest import mock
    from server.api import auth_postgres
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

# verify_password

def test_verify_password_correct(monkeypatch):
    called = {}
    def fake_checkpw(pw, hpw):
        called['args'] = (pw, hpw)
        return True
    monkeypatch.setattr(auth_postgres.bcrypt, 'checkpw', fake_checkpw)
    assert auth_postgres.verify_password('pw', 'hpw') is True
    assert called['args'][0] == b'pw'
    assert called['args'][1] == b'hpw'

def test_verify_password_incorrect(monkeypatch):
    monkeypatch.setattr(auth_postgres.bcrypt, 'checkpw', lambda pw, hpw: False)
    assert auth_postgres.verify_password('pw', 'hpw') is False

# get_password_hash

def test_get_password_hash(monkeypatch):
    def fake_hashpw(pw, salt):
        return b'hashedpw'
    def fake_gensalt():
        return b'salt'
    monkeypatch.setattr(auth_postgres.bcrypt, 'hashpw', fake_hashpw)
    monkeypatch.setattr(auth_postgres.bcrypt, 'gensalt', fake_gensalt)
    result = auth_postgres.get_password_hash('pw')
    assert result == 'hashedpw'

# get_user_by_email
import sys
import types
@pytest.mark.asyncio
async def test_get_user_by_email_found(monkeypatch):
    class FakeUser:
        id = 1
        email = 'a@b.com'
        full_name = 'A B'
        hashed_password = 'hpw'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'doctor'
        created_at = 'now'
        last_login = 'now'
        is_verified = True
        verification_token = 'tok'
        verification_token_expires = 'exp'
    class FakeResult:
        def scalar_one_or_none(self):
            return FakeUser()
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
    # Patch UserInDB
    fake_UserInDB = lambda **kwargs: kwargs
    monkeypatch.setattr(auth_postgres, 'UserInDB', fake_UserInDB)
    # Patch User
    monkeypatch.setattr(auth_postgres, 'User', type('User', (), {}))
    # Patch select
    monkeypatch.setattr(auth_postgres, 'select', lambda x: 'query')
    db = FakeDB()
    result = await auth_postgres.get_user_by_email('a@b.com', db)
    assert result['email'] == 'a@b.com'
    assert result['user_type'] == 'doctor'

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
    monkeypatch.setattr(auth_postgres, 'User', type('User', (), {}))
    monkeypatch.setattr(auth_postgres, 'select', lambda x: 'query')
    db = FakeDB()
    result = await auth_postgres.get_user_by_email('notfound', db)
    assert result is None

# authenticate_user
@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch):
    user_obj = type('User', (), {'hashed_password': 'hpw', 'email': 'a@b.com'})()
    async def fake_get_user_by_email(email, db):
        return type('UserInDB', (), {'hashed_password': 'hpw', 'email': 'a@b.com', 'is_verified': True})()
    def fake_verify_password(pw, hpw):
        return True
    class FakeResult:
        def scalar_one_or_none(self):
            return user_obj
    class FakeDB:
        async def execute(self, query):
            return FakeResult()
        async def commit(self):
            pass
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    monkeypatch.setattr(auth_postgres, 'verify_password', fake_verify_password)
    monkeypatch.setattr(auth_postgres, 'User', type('User', (), {}))
    monkeypatch.setattr(auth_postgres, 'select', lambda x: 'query')
    db = FakeDB()
    result = await auth_postgres.authenticate_user('a@b.com', 'pw', db)
    assert result.email == 'a@b.com'

@pytest.mark.asyncio
async def test_authenticate_user_fail(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    db = object()
    result = await auth_postgres.authenticate_user('no@b.com', 'pw', db)
    assert result is False

# create_access_token

def test_create_access_token(monkeypatch):
    called = {}
    def fake_encode(to_encode, secret, algorithm):
        called['args'] = (to_encode, secret, algorithm)
        return 'jwtstring'
    monkeypatch.setattr(auth_postgres, 'jwt', type('jwt', (), {'encode': staticmethod(fake_encode)}))
    monkeypatch.setattr(auth_postgres, 'SECRET_KEY', 'sk')
    monkeypatch.setattr(auth_postgres, 'ALGORITHM', 'HS256')
    monkeypatch.setattr(auth_postgres, 'ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    import datetime
    data = {'sub': 'user'}
    token = auth_postgres.create_access_token(data)
    assert token == 'jwtstring'
    assert 'exp' in called['args'][0]
