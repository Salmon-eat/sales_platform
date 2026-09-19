from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import RedisDep, SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: SessionDep, redis: RedisDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"unhealthy: {type(exc).__name__}") from exc
    return {"status": "ok"}
