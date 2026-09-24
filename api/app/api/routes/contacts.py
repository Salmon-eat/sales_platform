"""The seller's contacts, handed over one ad at a time.

The phone is never part of the ad page itself: a robot that walks the site collects nothing. It is
asked for here, when a person presses "show the number", and only for ads a visitor posted themselves —
the agency's own listings are answered through the application form, as before.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Listing, User
from app.schemas.chat import ContactOut

router = APIRouter(prefix="/contact", tags=["contacts"])

SHOWN_STATUSES = ("active", "paused")


@router.get("/{listing_id}", response_model=ContactOut)
async def contact(listing_id: int, session: SessionDep) -> ContactOut:
    listing = await session.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None or listing.status not in SHOWN_STATUSES or listing.owner_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    given = listing.contact or {}
    owner = await session.get(User, listing.owner_id)
    return ContactOut(
        name=given.get("name") or (owner.name if owner else None),
        phone=given.get("phone"),
        whatsapp=given.get("whatsapp"),
        telegram=given.get("telegram"),
        email=given.get("email"),
        can_chat=owner is not None and owner.is_active,
    )
