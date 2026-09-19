"""Bots on the public forms (applications, the site chat, employer requests).

Two layers:
- a honeypot: a field people never see; form-filling bots fill it. They get a normal-looking answer and
  nothing is stored, so they do not learn they were caught;
- Cloudflare Turnstile (free, invisible for most people): switched on by TURNSTILE_SECRET_KEY. Without the
  key only the honeypot and the per-IP limits work.
"""

import asyncio
import json
import logging
import urllib.parse
import urllib.request

from fastapi import HTTPException, status

from app.core.config import settings

log = logging.getLogger("bazarcito.antibot")

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def is_honeypot(website: str | None) -> bool:
    return bool(website and website.strip())


def _verify(token: str, ip: str | None) -> bool:
    data = {"secret": settings.turnstile_secret_key, "response": token}
    if ip:
        data["remoteip"] = ip
    request = urllib.request.Request(VERIFY_URL, data=urllib.parse.urlencode(data).encode(), method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 (fixed https URL)
        return bool(json.load(response).get("success"))


async def require_human(captcha: str | None, ip: str | None) -> None:
    """Turnstile check when it is switched on; 400 "captcha" makes the form show the check again."""
    if not settings.turnstile_secret_key:
        return
    if not captcha:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "captcha")
    try:
        ok = await asyncio.to_thread(_verify, captcha, ip)
    except OSError as exc:
        # Cloudflare unreachable from our server: a real person must not lose the application
        log.warning("turnstile unreachable, letting the form through: %s", exc)
        return
    if not ok:
        log.info("turnstile refused a form from %s", ip)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "captcha")
