"""Checking a firm's page before it appears, and marking one as verified."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import AdminLang, RedisDep, SessionDep, require_staff
from app.models import User
from app.schemas.company import CompanyRejectIn
from app.services import companies
from app.services.cache import bump_cache_version

router = APIRouter(prefix="/admin/companies", tags=["admin: companies"])

Staff = Annotated[User, Depends(require_staff)]


@router.get("/queue")
async def queue(session: SessionDep, user: Staff, lang: AdminLang) -> list[dict[str, Any]]:
    return await companies.queue(session, lang)


@router.post("/{company_id}/approve", status_code=204)
async def approve(
    company_id: int,
    session: SessionDep,
    redis: RedisDep,
    user: Staff,
    verified: bool = False,
) -> None:
    """`verified=true` means somebody has actually seen the firm's papers."""
    await companies.approve(session, company_id, user, verified)
    await bump_cache_version(redis)


@router.post("/{company_id}/reject", status_code=204)
async def reject(
    company_id: int, body: CompanyRejectIn, session: SessionDep, user: Staff
) -> None:
    await companies.reject(session, company_id, user, body.reason, body.note)
