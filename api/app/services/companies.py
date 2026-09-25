"""The directory of firms: writing one's own page, and finding somebody else's.

A firm goes through the same gate as an ad — a person reads it before it appears. Its rating comes
from the reviews of the person who owns it, so a company cannot collect praise separately from the
human being answering the phone.
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.slug import slugify
from app.models import Category, Company, Listing, Location, User
from app.models.company import MAX_CATEGORIES
from app.models.i18n import tr
from app.schemas.company import CompanyCard, CompanyIn, CompanyOut, MyCompanyOut
from app.services import reviews

PUBLIC = ("active",)
EDITABLE = ("draft", "pending", "active", "rejected", "hidden")


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


async def _free_slug(session: AsyncSession, name: str, company_id: int | None) -> str:
    """The firm's name as an address; a second firm with the same name gets a number."""
    base = slugify(name)[:120] or "empresa"
    candidate = base
    for suffix in range(2, 60):
        clash = await session.scalar(
            select(Company.id).where(Company.slug == candidate, Company.id != (company_id or 0))
        )
        if clash is None:
            return candidate
        candidate = f"{base}-{suffix}"
    return f"{base}-{datetime.now(UTC):%Y%m%d%H%M%S}"


async def get_own(session: AsyncSession, user: User) -> Company | None:
    return await session.scalar(select(Company).where(Company.owner_id == user.id))


async def save(session: AsyncSession, user: User, data: CompanyIn) -> Company:
    if len(data.category_ids) > MAX_CATEGORIES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "too_many_categories")
    if data.category_ids:
        found = await session.scalars(select(Category.id).where(Category.id.in_(data.category_ids)))
        if len(set(found.all())) != len(data.category_ids):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_not_found")
    if data.city_id is not None:
        city = await session.get(Location, data.city_id)
        if city is None or city.level not in ("municipio", "localidad"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "city_not_found")

    company = await get_own(session, user)
    if company is None:
        company = Company(owner_id=user.id, name=data.name, slug="")
        session.add(company)
    elif company.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_editable")

    renamed = company.name != data.name or not company.slug
    for field, value in data.model_dump().items():
        setattr(company, field, value)
    if renamed:
        company.slug = await _free_slug(session, data.name, company.id)
    # an edited page goes back for a look, exactly like an edited ad
    if company.status == "active":
        company.status = "pending"
    await session.commit()
    await session.refresh(company)
    return company


async def act(session: AsyncSession, user: User, action: str) -> Company:
    company = await get_own(session, user)
    if company is None:
        raise _not_found()
    if action == "submit":
        if company.status not in ("draft", "rejected", "hidden"):
            raise HTTPException(status.HTTP_409_CONFLICT, "not_submittable")
        company.status = "pending"
        company.reject_reason = company.reject_note = None
    elif action == "hide":
        company.status = "hidden"
    elif action == "reopen":
        if company.status != "hidden":
            raise HTTPException(status.HTTP_409_CONFLICT, "not_hidden")
        company.status = "pending"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown_action")
    await session.commit()
    await session.refresh(company)
    return company


async def remove(session: AsyncSession, user: User) -> None:
    company = await get_own(session, user)
    if company is None:
        raise _not_found()
    await session.delete(company)
    await session.commit()


# ---------------------------------------------------------------------------- moderation


async def queue(session: AsyncSession, lang: str) -> list[dict]:
    rows = (
        await session.scalars(
            select(Company).where(Company.status == "pending").order_by(Company.updated_at)
        )
    ).all()
    out = []
    for company in rows:
        owner = await session.get(User, company.owner_id)
        out.append(
            {
                **(await card(session, company, lang)).model_dump(),
                "owner_name": (owner.name or owner.email) if owner else None,
                "owner_id": company.owner_id,
                "address": company.address,
                "hours": company.hours,
                "phone": company.phone,
                "email": company.email,
                "site": company.site,
                "updated_at": company.updated_at,
            }
        )
    return out


async def approve(session: AsyncSession, company_id: int, staff: User, verified: bool) -> None:
    company = await session.get(Company, company_id)
    if company is None:
        raise _not_found()
    now = datetime.now(UTC)
    company.status = "active"
    company.reject_reason = company.reject_note = None
    company.moderated_by, company.moderated_at = staff.id, now
    if verified:
        company.is_verified, company.verified_at = True, now
    await session.commit()


async def reject(
    session: AsyncSession, company_id: int, staff: User, reason: str, note: str | None
) -> None:
    company = await session.get(Company, company_id)
    if company is None:
        raise _not_found()
    company.status = "rejected"
    company.reject_reason, company.reject_note = reason, note
    company.moderated_by, company.moderated_at = staff.id, datetime.now(UTC)
    await session.commit()


# ---------------------------------------------------------------------------- the catalogue


async def _category_names(session: AsyncSession, ids: list[int], lang: str) -> list[str]:
    if not ids:
        return []
    rows = await session.scalars(select(Category).where(Category.id.in_(ids)))
    return [tr(c.name, lang) for c in rows]


async def card(session: AsyncSession, company: Company, lang: str) -> CompanyCard:
    city = await session.get(Location, company.city_id) if company.city_id else None
    average, count = await reviews.rating_of(session, company.owner_id)
    listings = (
        await session.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.owner_id == company.owner_id, Listing.status == "active")
        )
        or 0
    )
    return CompanyCard(
        id=company.id,
        slug=company.slug,
        name=company.name,
        about=company.about,
        lang=company.lang,
        city_name=tr(city.names, lang) if city else None,
        categories=await _category_names(session, list(company.category_ids or []), lang),
        logo=company.logo,
        is_verified=company.is_verified,
        rating=average,
        reviews_count=count,
        listings_count=listings,
    )


async def detail(session: AsyncSession, company: Company, lang: str) -> CompanyOut:
    base = await card(session, company, lang)
    return CompanyOut(
        **base.model_dump(),
        owner_id=company.owner_id,
        address=company.address,
        hours=company.hours,
        site=company.site,
        created_at=company.created_at,
    )


async def mine_out(session: AsyncSession, company: Company, lang: str) -> MyCompanyOut:
    base = await detail(session, company, lang)
    return MyCompanyOut(
        **base.model_dump(),
        status=company.status,
        reject_reason=company.reject_reason,
        reject_note=company.reject_note,
        category_ids=list(company.category_ids or []),
        city_id=company.city_id,
        phone=company.phone,
        whatsapp=company.whatsapp,
        telegram=company.telegram,
        email=company.email,
        updated_at=company.updated_at,
    )


async def by_slug(session: AsyncSession, slug: str) -> Company:
    company = await session.scalar(
        select(Company).where(Company.slug == slug, Company.status.in_(PUBLIC))
    )
    if company is None:
        raise _not_found()
    return company


async def catalogue(
    session: AsyncSession,
    lang: str,
    q: str | None = None,
    category_id: int | None = None,
    city_slug: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    conds = [Company.status.in_(PUBLIC)]
    if category_id:
        # the chosen category or any of its children
        children = select(Category.id).where(Category.parent_id == category_id)
        ids = [category_id, *(await session.scalars(children)).all()]
        conds.append(Company.category_ids.overlap(ids))
    if city_slug:
        city = await session.scalar(select(Location).where(Location.slug == city_slug))
        conds.append(Company.city_id == (city.id if city else 0))
    if q:
        needle = f"%{q.strip()}%"
        conds.append(or_(Company.name.ilike(needle), Company.about.ilike(needle)))

    total = await session.scalar(select(func.count()).select_from(Company).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(Company)
            .where(*conds)
            # verified first, then the ones people actually rated
            .order_by(Company.is_verified.desc(), Company.updated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return {
        "items": [await card(session, row, lang) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def company_listings(session: AsyncSession, company: Company, lang: str):
    from app.services.listings import public_cards

    rows = (
        await session.scalars(
            select(Listing)
            .where(Listing.owner_id == company.owner_id, Listing.status == "active")
            .options(selectinload(Listing.translations))
            .order_by(Listing.published_at.desc())
            .limit(12)
        )
    ).all()
    return await public_cards(session, list(rows), lang)
