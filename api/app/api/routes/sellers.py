"""The public page of somebody who sells: their rating, their reviews, their ads."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.common import Lang
from app.services import reviews

router = APIRouter(prefix="/sellers", tags=["sellers"])


@router.get("/{seller_id}")
async def seller(seller_id: int, session: SessionDep, lang: Lang = "es") -> dict[str, Any]:
    return await reviews.seller_page(session, seller_id, lang)
