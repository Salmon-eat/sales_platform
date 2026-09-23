"""The visitor's own ads: write one, attach photos, send it for checking, close it.

Everything here is about the person's own rows only: each handler looks the ad up by id *and* owner,
so an id guessed from someone else's page leads nowhere.
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models.listing import MAX_PHOTOS
from app.schemas.common import Lang
from app.schemas.my import MyActionIn, MyListingIn, MyListingItem, MyListingOut, PhotoOut
from app.services import my_listings, photos

router = APIRouter(prefix="/my", tags=["my"])


@router.get("/listings", response_model=list[MyListingItem])
async def my_ads(user: CurrentUser, session: SessionDep, lang: Lang = "es") -> list[MyListingItem]:
    return await my_listings.mine(session, user, lang)


@router.post("/listings", response_model=MyListingOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: MyListingIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.save(session, user, body)
    return await my_listings.detail_out(session, listing, lang)


@router.get("/listings/{listing_id}", response_model=MyListingOut)
async def one(
    listing_id: int, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    return await my_listings.detail_out(session, listing, lang)


@router.put("/listings/{listing_id}", response_model=MyListingOut)
async def update(
    listing_id: int, body: MyListingIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    listing = await my_listings.save(session, user, body, listing)
    return await my_listings.detail_out(session, listing, lang)


@router.post("/listings/{listing_id}/actions", response_model=MyListingOut)
async def act(
    listing_id: int, body: MyActionIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    listing = await my_listings.act(session, user, listing, body.action)
    return await my_listings.detail_out(session, listing, lang)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(listing_id: int, user: CurrentUser, session: SessionDep) -> None:
    listing = await my_listings.get_own(session, user, listing_id)
    await my_listings.remove(session, listing)


@router.post("/listings/{listing_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def add_photo(
    listing_id: int, request: Request, user: CurrentUser, session: SessionDep
) -> PhotoOut:
    """One photo as the raw request body, like the CV upload: no form encoding, no extra library."""
    listing = await my_listings.get_own(session, user, listing_id)
    if int(request.headers.get("content-length") or 0) > photos.MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > photos.MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    row = await my_listings.add_photo(session, user, listing, bytes(data))
    return PhotoOut(
        id=row.id, path=row.path, thumb=photos.thumb_path(row.path), width=row.width, height=row.height
    )


@router.delete("/listings/{listing_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_photo(
    listing_id: int, photo_id: int, user: CurrentUser, session: SessionDep
) -> None:
    listing = await my_listings.get_own(session, user, listing_id)
    await my_listings.drop_photo(session, listing, photo_id)


@router.get("/limits")
async def limits(user: CurrentUser, session: SessionDep) -> dict[str, int]:
    """What the form needs to know before it lets someone start another ad."""
    return {
        "open": await my_listings.count_open(session, user),
        "max_listings": settings.listings_per_user,
        "max_photos": MAX_PHOTOS,
        "days": settings.listing_days,
    }
