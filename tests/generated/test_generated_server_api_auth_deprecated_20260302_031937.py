import pytest
import sys

pytestmark = pytest.mark.asyncio

symbols = [
    'login_for_access_token',
    'login_for_mobile_access_token',
    'register_user',
    'read_users_me',
    'verify_email',
    'resend_verification',
    'forgot_password',
    'reset_password',
]

try:
    import server.api.auth_deprecated as auth_deprecated
except ImportError:
    auth_deprecated = None

@pytest.mark.skipif(auth_deprecated is None, reason='Import failed')
@pytest.mark.asyncio
@pytest.mark.parametrize('func_name,args', [
    ('login_for_mobile_access_token', ()),
    ('register_user', ()),
    ('read_users_me', ()),
    ('verify_email', ("sometoken",)),
    ('resend_verification', ()),
    ('forgot_password', ()),
    ('reset_password', ()),
])
async def test_deprecated_endpoints_raise_501(func_name, args):
    func = getattr(auth_deprecated, func_name)
    with pytest.raises(Exception) as excinfo:
        if args:
            await func(*args)
        else:
            # Provide dummy args for endpoints that require them
            try:
                await func(None, None, None)
            except TypeError:
                await func(None, None)
    assert '501' in str(excinfo.value) or 'Not Implemented' in str(excinfo.value)
