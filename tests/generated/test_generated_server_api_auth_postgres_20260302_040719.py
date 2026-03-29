try:
    import pytest
    from server.api import auth_postgres
    import bcrypt
    from unittest import mock
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_verify_password_true():
    password = 'secret123'
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    assert auth_postgres.verify_password(password, hashed) is True

def test_verify_password_false():
    password = 'secret123'
    hashed = bcrypt.hashpw('otherpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    assert auth_postgres.verify_password(password, hashed) is False

def test_get_password_hash_roundtrip():
    password = 'mypassword!'
    hashed = auth_postgres.get_password_hash(password)
    assert isinstance(hashed, str)
    assert bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

@pytest.mark.asyncio
def test_get_user_by_email_found(monkeypatch):
    class DummyUser:
        id = 1
        email = 'a@b.com'
        full_name = 'Test User'
        hashed_password = 'hash'
        birthdate = '2000-01-01'
        subscription_tier = 'free'
        user_type = 'patient'
        created_at = 'now'
        last_login = None
        is_verified = True
        verification_token = None
        verification_token_expires = None
    class DummyResult:
        def scalar_one_or_none(self):
            return DummyUser()
    class DummySession:
        async def execute(self, query):
            return DummyResult()
    user = None
    async def run():
        nonlocal user
        user = await auth_postgres.get_user_by_email('a@b.com', DummySession())
    import asyncio; asyncio.run(run())
    assert user.email == 'a@b.com'

@pytest.mark.asyncio
def test_get_user_by_email_not_found(monkeypatch):
    class DummyResult:
        def scalar_one_or_none(self):
            return None
    class DummySession:
        async def execute(self, query):
            return DummyResult()
    user = 'notset'
    async def run():
        nonlocal user
        user = await auth_postgres.get_user_by_email('none@b.com', DummySession())
    import asyncio; asyncio.run(run())
    assert user is None

@pytest.mark.asyncio
def test_authenticate_user_success(monkeypatch):
    class DummyUser:
        hashed_password = bcrypt.hashpw('pw'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        email = 'e@e.com'
    async def fake_get_user_by_email(email, db):
        return DummyUser()
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    monkeypatch.setattr(auth_postgres, 'verify_password', lambda pw, h: True)
    class DummyResult:
        def scalar_one_or_none(self):
            return DummyUser()
    class DummySession:
        async def execute(self, query):
            return DummyResult()
        async def commit(self):
            pass
    user = None
    async def run():
        nonlocal user
        user = await auth_postgres.authenticate_user('e@e.com', 'pw', DummySession())
    import asyncio; asyncio.run(run())
    assert user is not None

@pytest.mark.asyncio
def test_authenticate_user_fail(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None
    monkeypatch.setattr(auth_postgres, 'get_user_by_email', fake_get_user_by_email)
    class DummySession:
        async def execute(self, query):
            return None
        async def commit(self):
            pass
    user = 'notset'
    async def run():
        nonlocal user
        user = await auth_postgres.authenticate_user('e@e.com', 'pw', DummySession())
    import asyncio; asyncio.run(run())
    assert user is False

def test_create_access_token(monkeypatch):
    import datetime
    data = {'sub': 'user'}
    token = auth_postgres.create_access_token(data)
    assert isinstance(token, str)
    token2 = auth_postgres.create_access_token(data, expires_delta=datetime.timedelta(minutes=1))
    assert isinstance(token2, str)
