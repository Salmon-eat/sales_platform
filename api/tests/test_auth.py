"""Google ID-token checks and settings guards for the staff sign-in (admin spec §1)."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import GoogleTokenError, decode_google_token, hash_token, new_session_token

CLIENT_ID = "123-abc.apps.googleusercontent.com"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def google_token(key=KEY, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "1098765",
        "email": "Manager@Example.com",
        "email_verified": True,
        "name": "Olena",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256")


def decode(token: str):
    return decode_google_token(token, CLIENT_ID, KEY.public_key())


def test_valid_token_gives_lowercased_email():
    identity = decode(google_token())
    assert identity.email == "manager@example.com"
    assert identity.sub == "1098765"
    assert identity.name == "Olena"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "someone-else.apps.googleusercontent.com"},  # token issued for another site
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 3600},  # expired
        {"email_verified": False},
        {"email": None},
    ],
)
def test_rejected_tokens(overrides):
    with pytest.raises(GoogleTokenError):
        decode(google_token(**overrides))


def test_foreign_signature_is_rejected():
    with pytest.raises(GoogleTokenError):
        decode(google_token(key=OTHER_KEY))


def test_session_token_is_stored_as_hash_only():
    token, stored = new_session_token()
    assert token != stored
    assert hash_token(token) == stored
    assert len(stored) == 64


def test_dev_login_is_refused_in_production():
    with pytest.raises(ValidationError):
        Settings(env="production", secret_key="x" * 40, admin_dev_login=True)
    assert Settings(env="development", admin_dev_login=True).admin_dev_login
