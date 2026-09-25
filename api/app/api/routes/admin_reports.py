"""The complaints queue and switching an account off.

Taking an ad down is a judgement, so a person makes it. Blocking somebody takes their ads down with
them — otherwise a blocked account keeps selling.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import AdminLang, RedisDep, SessionDep, require_admin, require_staff
from app.models import User
from app.services import reports
from app.services.cache import bump_cache_version

router = APIRouter(prefix="/admin/reports", tags=["admin: reports"])

Staff = Annotated[User, Depends(require_staff)]
Admin = Annotated[User, Depends(require_admin)]


class ResolveIn(BaseModel):
    action: Literal["accept", "reject"]
    # filled in only when the person behind the ad should be switched off as well
    block_reason: str | None = Field(None, max_length=200)


class BlockIn(BaseModel):
    reason: str = Field(min_length=3, max_length=200)


@router.get("/queue")
async def queue(
    session: SessionDep,
    user: Staff,
    lang: AdminLang,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict]:
    return await reports.queue(session, lang, limit)


@router.get("/count")
async def count(session: SessionDep, user: Staff) -> dict[str, int]:
    return {"reports": await reports.waiting(session)}


@router.post("/{report_id}/resolve", status_code=204)
async def resolve(
    report_id: int, body: ResolveIn, session: SessionDep, redis: RedisDep, user: Staff
) -> None:
    await reports.resolve(session, report_id, body.action, user, body.block_reason)
    await bump_cache_version(redis)


@router.post("/users/{user_id}/block", status_code=204)
async def block(
    user_id: int, body: BlockIn, session: SessionDep, redis: RedisDep, user: Admin
) -> None:
    """Admins only: this takes away somebody's account and everything they have on the site."""
    await reports.block_user(session, user_id, body.reason)
    await session.commit()
    await bump_cache_version(redis)


@router.post("/users/{user_id}/unblock", status_code=204)
async def unblock(user_id: int, session: SessionDep, redis: RedisDep, user: Admin) -> None:
    await reports.unblock_user(session, user_id)
    await bump_cache_version(redis)
