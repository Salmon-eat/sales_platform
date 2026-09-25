"""Per-IP request limits for the whole API: floods, scraping, brute force and form spam.

Counters live in Redis (one-minute windows), so every worker process shares them. The visitor's IP comes
from Caddy (X-Forwarded-For, which Caddy overwrites for outside clients, so it cannot be forged). Requests
from private addresses are the site's own server (Next.js pages, the worker) and are not limited; the
endpoints with their own stricter limits (applications, chat, sign-in) keep them on top of these.
"""

import ipaddress
import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger("bazarcito.ratelimit")

WINDOW = 60  # seconds

# (path prefix, methods or None for all, requests per minute per IP); the first match wins
RULES: tuple[tuple[str, frozenset[str] | None, int], ...] = (
    ("/v1/health", None, 0),  # 0 = no limit
    ("/v1/internal/", None, 0),  # the Telegram bot, checked by its token
    ("/v1/auth/", frozenset({"POST"}), 10),
    ("/v1/account/code", None, 5),  # asking for a sign-in code
    ("/v1/account/session", None, 10),  # trying a code
    ("/v1/account/google", None, 10),
    ("/v1/account/telegram", None, 10),
    ("/v1/applications", frozenset({"POST"}), 10),
    ("/v1/employer-requests", frozenset({"POST"}), 5),
    # asking for a seller's phone: a person presses it a few times, a harvester thousands
    ("/v1/contact/", None, 20),
    ("/v1/reports", frozenset({"POST"}), 10),
    ("/v1/my/chats", frozenset({"POST"}), 20),
    ("/v1/chat/", frozenset({"POST"}), 20),
    ("/v1/chat/", None, 30),  # the open chat window polls every 8 s
    ("/v1/events", None, 120),
    ("/v1/suggest", None, 90),  # typing in the search box
    ("/v1/go/", None, 30),
    ("/v1/", frozenset({"POST", "PUT", "PATCH", "DELETE"}), 30),
    ("/v1/", None, 240),
)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def is_internal(ip: str | None) -> bool:
    """The site's own containers (and the developer's machine): private or loopback addresses."""
    if not ip:
        return True
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


def rule_for(path: str, method: str) -> tuple[str, int] | None:
    for prefix, methods, limit in RULES:
        if path.startswith(prefix) and (methods is None or method in methods):
            return (f"{prefix}:{'w' if methods else 'a'}", limit) if limit else None
    return None


async def over_limit(redis: Redis, ip: str, bucket: str, limit: int) -> bool:
    key = f"rl:ip:{bucket}:{ip}"
    try:
        async with redis.pipeline(transaction=False) as pipe:
            pipe.incr(key)
            pipe.expire(key, WINDOW, nx=True)
            count, _ = await pipe.execute()
    except RedisError:
        return False  # never take the site down because Redis is
    return count > limit


def too_many() -> Response:
    return JSONResponse(
        {"detail": "Too many requests, try again in a minute"},
        status_code=429,
        headers={"Retry-After": str(WINDOW)},
    )
