"""Session tokens and Google ID-token verification (admin spec §1)."""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from functools import lru_cache

import jwt

from app.core.config import settings

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ["accounts.google.com", "https://accounts.google.com"]


def new_session_token() -> tuple[str, str]:
    """(token for the cookie, SHA-256 for the database): a stolen database does not give live sessions."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class GoogleTokenError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str | None
    picture: str | None


@lru_cache(maxsize=1)
def _google_keys() -> jwt.PyJWKClient:
    # keys are cached in the client and refetched when Google rotates them
    return jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600)


def decode_google_token(credential: str, client_id: str, key: object) -> GoogleIdentity:
    """Checks signature, audience, issuer, expiry and a verified email."""
    try:
        claims = jwt.decode(
            credential,
            key,  # type: ignore[arg-type]
            algorithms=["RS256"],
            audience=client_id,
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iat", "sub", "email"]},
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        raise GoogleTokenError(str(exc)) from exc
    if claims.get("email_verified") is not True:
        raise GoogleTokenError("email is not verified by Google")
    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(claims["email"]).lower(),
        name=claims.get("name"),
        picture=claims.get("picture"),
    )


async def verify_google_token(credential: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise GoogleTokenError("GOOGLE_CLIENT_ID is not configured")
    try:
        # PyJWKClient uses blocking urllib: keep it off the event loop
        signing_key = await asyncio.to_thread(_google_keys().get_signing_key_from_jwt, credential)
    except jwt.PyJWTError as exc:
        raise GoogleTokenError(str(exc)) from exc
    return decode_google_token(credential, settings.google_client_id, signing_key.key)
