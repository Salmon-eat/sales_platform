import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core import ratelimit
from app.core.config import settings
from app.core.db import engine
from app.core.redis import redis

API_PREFIX = "/v1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
action_log = logging.getLogger("bazarcito.actions")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await redis.aclose()
    await engine.dispose()


CallNext = Callable[[Request], Awaitable[Response]]


async def log_admin_actions(request: Request, call_next: CallNext) -> Response:
    """Every change in /admin is written to the server log with the user id (admin spec §9;
    a full action journal in the database is phase 2)."""
    response = await call_next(request)
    if request.url.path.startswith(f"{API_PREFIX}/admin") and request.method != "GET":
        action_log.info(
            "user_id=%s %s %s -> %s",
            getattr(request.state, "user_id", None),
            request.method,
            request.url.path,
            response.status_code,
        )
    return response


NO_STORE = (f"{API_PREFIX}/admin", f"{API_PREFIX}/auth", f"{API_PREFIX}/chat", f"{API_PREFIX}/internal")


async def protect(request: Request, call_next: CallNext) -> Response:
    """Per-IP limits before any work is done; private answers are never cached on the way."""
    path = request.url.path
    ip = ratelimit.client_ip(request)
    rule = None if ratelimit.is_internal(ip) else ratelimit.rule_for(path, request.method)
    if rule and ip and await ratelimit.over_limit(redis, ip, *rule):
        ratelimit.log.warning("rate limit %s %s %s", ip, request.method, path)
        return ratelimit.too_many()
    response = await call_next(request)
    if path.startswith(NO_STORE):
        response.headers["Cache-Control"] = "no-store"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


def create_app() -> FastAPI:
    docs = not settings.is_production
    app = FastAPI(
        title="Citobazar API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs" if docs else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if docs else None,
    )
    app.middleware("http")(log_admin_actions)
    app.middleware("http")(protect)  # added last = runs first
    app.include_router(api_router, prefix=API_PREFIX)
    # Photos of ads. In production Caddy serves the same folder itself and never gets here; this mount
    # is what makes the photos work in local development, and a fallback if the file server is off.
    media = Path(settings.media_root)
    media.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media), name="media")
    return app


app = create_app()
