"""Reporting an ad: open to anyone reading the site, signed in or not."""

from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import OptionalUser, SessionDep
from app.core.ratelimit import client_ip
from app.models.report import MAX_NOTE, REPORT_REASONS
from app.services import reports

router = APIRouter(prefix="/reports", tags=["reports"])

Reason = Literal[REPORT_REASONS]  # type: ignore[valid-type]


class ReportIn(BaseModel):
    listing_id: int
    reason: Reason
    note: str | None = Field(None, max_length=MAX_NOTE)

    @field_validator("note")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def report(
    body: ReportIn, request: Request, session: SessionDep, user: OptionalUser
) -> dict[str, bool]:
    """Always the same answer: nobody learns whether their complaint was the first or the tenth."""
    await reports.create(session, body.listing_id, body.reason, body.note, user, client_ip(request))
    return {"received": True}
