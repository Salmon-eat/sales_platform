"""The public directory of firms and one firm's page."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Company
from app.schemas.common import Lang
from app.schemas.company import CompanyContactOut
from app.services import companies

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def catalogue(
    session: SessionDep,
    lang: Lang = "es",
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: int | None = None,
    city: Annotated[str | None, Query(max_length=120, pattern=r"^[a-z0-9-]+$")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, Any]:
    return await companies.catalogue(session, lang, q, category_id, city, page, per_page)


@router.get("/{slug}")
async def company(slug: str, session: SessionDep, lang: Lang = "es") -> dict[str, Any]:
    firm = await companies.by_slug(session, slug)
    return {
        **(await companies.detail(session, firm, lang)).model_dump(),
        "reviews": await _reviews(session, firm.owner_id),
        "listings": await companies.company_listings(session, firm, lang),
    }


async def _reviews(session: SessionDep, owner_id: int) -> list[dict]:
    from app.services import reviews

    return await reviews.about(session, owner_id)


@router.get("/{slug}/contact", response_model=CompanyContactOut)
async def contact(slug: str, session: SessionDep) -> CompanyContactOut:
    """Handed over on a press, like a seller's phone: never printed into the page itself."""
    firm = await session.scalar(select(Company).where(Company.slug == slug, Company.status == "active"))
    if firm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return CompanyContactOut(
        phone=firm.phone, whatsapp=firm.whatsapp, telegram=firm.telegram, email=firm.email
    )
