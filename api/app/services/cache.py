import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, TypeAdapter
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Bumped on every content change -> all versioned cache keys become stale at once.
CACHE_VERSION_KEY = "cache:version"
# Bumped only when taxonomy or locations change (rebuilds in-process dictionaries, e.g. query understanding).
TAXONOMY_VERSION_KEY = "cache:taxonomy_version"


async def _version(redis: Redis) -> str:
    return await redis.get(CACHE_VERSION_KEY) or "0"


async def bump_cache_version(redis: Redis, *, taxonomy: bool = False) -> None:
    try:
        await redis.incr(CACHE_VERSION_KEY)
        if taxonomy:
            await redis.incr(TAXONOMY_VERSION_KEY)
    except RedisError:
        logger.exception("failed to bump cache version")


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()


async def cached[T](
    redis: Redis,
    prefix: str,
    params: Any,
    ttl: int,
    type_: type[T],
    factory: Callable[[], Awaitable[T]],
) -> T:
    """Read-through cache. Redis being down degrades to a direct DB query, never to an error."""
    adapter = TypeAdapter(type_)
    key = None
    try:
        key = f"{prefix}:v{await _version(redis)}:{_digest(params)}"
        if (hit := await redis.get(key)) is not None:
            return adapter.validate_json(hit)
    except RedisError:
        logger.warning("redis unavailable, skipping cache for %s", prefix)

    value = await factory()

    if key is not None:
        try:
            await redis.set(key, adapter.dump_json(value), ex=ttl)
        except RedisError:
            pass
    return value


def params_of(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)
