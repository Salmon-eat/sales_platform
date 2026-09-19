"""Listings for managers and admins (spec §9: CRUD + translations, roles, BOLA checks)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminLang, RedisDep, SessionDep, require_staff
from app.core.db import SessionLocal
from app.models import Category, Listing, ListingTranslation, User
from app.schemas.common import Page
from app.schemas.listing import (
    AdminListingDetail,
    AdminListingItem,
    ListingActionIn,
    ListingIn,
    ListingStatus,
)
from app.seo.counts import recount_seo_pages
from app.services.cache import bump_cache_version
from app.services.listings import (
    admin_detail,
    admin_items,
    ensure_can_edit,
    get_listing,
    perform_action,
    save_listing,
)

router = APIRouter(prefix="/admin/listings", tags=["admin: listings"])

MAX_LIMIT = 100
Staff = Annotated[User, Depends(require_staff)]


async def _recount_seo() -> None:
    async with SessionLocal() as session:
        await recount_seo_pages(session)


@router.get("", response_model=Page[AdminListingItem])
async def list_listings(
    session: SessionDep,
    user: Staff,
    lang: AdminLang,
    status_: Annotated[ListingStatus | None, Query(alias="status")] = None,
    category_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    mine: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 30,
) -> Page[AdminListingItem]:
    conds = []
    if status_:
        conds.append(Listing.status == status_)
    if category_id:
        children = select(Category.id).where(Category.parent_id == category_id)
        conds.append(or_(Listing.category_id == category_id, Listing.category_id.in_(children)))
    if mine:
        conds.append(Listing.created_by == user.id)
    if q:
        needle = f"%{q.strip()}%"
        conds.append(
            or_(
                Listing.id == int(q) if q.strip().isdigit() else False,
                exists().where(
                    ListingTranslation.listing_id == Listing.id, ListingTranslation.title.ilike(needle)
                ),
                Listing.employer_name.ilike(needle),
            )
        )

    total = await session.scalar(select(func.count()).select_from(Listing).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(Listing)
            .where(*conds)
            .options(selectinload(Listing.translations))
            .order_by(Listing.updated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return Page(
        items=await admin_items(session, user, list(rows), lang), total=total, page=page, per_page=per_page
    )


@router.get("/{listing_id}", response_model=AdminListingDetail)
async def get_one(listing_id: int, session: SessionDep, user: Staff, lang: AdminLang) -> AdminListingDetail:
    return await admin_detail(session, user, await get_listing(session, listing_id), lang)


@router.post("", response_model=AdminListingDetail, status_code=status.HTTP_201_CREATED)
async def create(
    body: ListingIn, session: SessionDep, redis: RedisDep, user: Staff, lang: AdminLang
) -> AdminListingDetail:
    listing = await save_listing(session, user, body)
    await bump_cache_version(redis)
    return await admin_detail(session, user, listing, lang)


@router.put("/{listing_id}", response_model=AdminListingDetail)
async def replace(
    listing_id: int, body: ListingIn, session: SessionDep, redis: RedisDep, user: Staff, lang: AdminLang
) -> AdminListingDetail:
    listing = await get_listing(session, listing_id)
    ensure_can_edit(user, listing)
    listing = await save_listing(session, user, body, listing)
    await bump_cache_version(redis)
    return await admin_detail(session, user, listing, lang)


@router.post("/{listing_id}/actions", response_model=AdminListingDetail)
async def action(
    listing_id: int,
    body: ListingActionIn,
    session: SessionDep,
    redis: RedisDep,
    user: Staff,
    lang: AdminLang,
    background: BackgroundTasks,
) -> AdminListingDetail:
    """publish | pause | resume | close | extend (days)."""
    listing = await get_listing(session, listing_id)
    ensure_can_edit(user, listing)
    listing = await perform_action(session, listing, body.action, body.days)
    await bump_cache_version(redis)
    background.add_task(_recount_seo)
    return await admin_detail(session, user, listing, lang)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(listing_id: int, session: SessionDep, user: Staff, lang: AdminLang) -> None:
    listing = await get_listing(session, listing_id)
    ensure_can_edit(user, listing)
    if listing.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "delete_only_draft")
    await session.delete(listing)
    await session.commit()
