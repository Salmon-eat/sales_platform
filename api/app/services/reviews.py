"""Reviews of a seller, and the public page that shows them.

One rule carries the whole thing: only somebody who actually wrote to the seller about one of their
ads may review them. A rating from a person who never got in touch tells the next buyer nothing, and
is the easiest thing in the world to abuse.
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Listing, SellerReview, User
from app.services.listings import public_cards

SELLER_ADS = 12


async def _talked_to(session: AsyncSession, author: User, seller_id: int) -> bool:
    return bool(
        await session.scalar(
            select(Conversation.id)
            .where(Conversation.buyer_id == author.id, Conversation.seller_id == seller_id)
            .limit(1)
        )
    )


async def rating_of(session: AsyncSession, seller_id: int) -> tuple[float | None, int]:
    row = (
        await session.execute(
            select(func.avg(SellerReview.rating), func.count())
            .where(SellerReview.seller_id == seller_id, SellerReview.is_hidden.is_(False))
        )
    ).one()
    average, count = row
    return (round(float(average), 2) if average is not None else None), int(count or 0)


async def leave(
    session: AsyncSession,
    author: User,
    seller_id: int,
    rating: int,
    text: str,
    listing_id: int | None,
) -> SellerReview:
    if seller_id == author.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_yourself")
    seller = await session.get(User, seller_id)
    if seller is None or seller.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if not await _talked_to(session, author, seller_id):
        # writing to them about an ad is what makes a review possible
        raise HTTPException(status.HTTP_409_CONFLICT, "no_deal")

    review = await session.scalar(
        select(SellerReview).where(
            SellerReview.seller_id == seller_id, SellerReview.author_id == author.id
        )
    )
    if review is None:
        review = SellerReview(seller_id=seller_id, author_id=author.id)
        session.add(review)
    review.rating, review.text, review.listing_id = rating, text, listing_id
    await session.commit()
    await session.refresh(review)
    return review


async def remove(session: AsyncSession, author: User, seller_id: int) -> None:
    review = await session.scalar(
        select(SellerReview).where(
            SellerReview.seller_id == seller_id, SellerReview.author_id == author.id
        )
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    await session.delete(review)
    await session.commit()


async def answer(session: AsyncSession, seller: User, review_id: int, text: str) -> SellerReview:
    """The seller's reply; only about themselves, and only once written it can be changed."""
    review = await session.scalar(
        select(SellerReview).where(SellerReview.id == review_id, SellerReview.seller_id == seller.id)
    )
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    review.reply, review.replied_at = text, datetime.now(UTC)
    await session.commit()
    await session.refresh(review)
    return review


async def _name(session: AsyncSession, user_id: int) -> str:
    person = await session.get(User, user_id)
    if person is None or person.deleted_at is not None:
        return "—"
    return person.name or (person.email.split("@")[0] if person.email else "—")


async def as_dict(session: AsyncSession, review: SellerReview) -> dict:
    return {
        "id": review.id,
        "rating": review.rating,
        "text": review.text,
        "reply": review.reply,
        "replied_at": review.replied_at,
        "author_name": await _name(session, review.author_id),
        "seller_name": await _name(session, review.seller_id),
        "listing_id": review.listing_id,
        "created_at": review.created_at,
    }


async def about(session: AsyncSession, seller_id: int, limit: int = 20) -> list[dict]:
    rows = (
        await session.scalars(
            select(SellerReview)
            .where(SellerReview.seller_id == seller_id, SellerReview.is_hidden.is_(False))
            .order_by(SellerReview.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [await as_dict(session, row) for row in rows]


async def written_by(session: AsyncSession, author: User) -> list[dict]:
    rows = (
        await session.scalars(
            select(SellerReview)
            .where(SellerReview.author_id == author.id)
            .order_by(SellerReview.created_at.desc())
        )
    ).all()
    return [await as_dict(session, row) for row in rows]


async def seller_page(session: AsyncSession, seller_id: int, lang: str) -> dict:
    """The public page of a person who sells: who they are, how they are rated, what they have now."""
    seller = await session.get(User, seller_id)
    if seller is None or not seller.is_active or seller.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    average, count = await rating_of(session, seller_id)
    rows = (
        await session.scalars(
            select(Listing)
            .where(Listing.owner_id == seller_id, Listing.status == "active")
            .options(selectinload(Listing.translations))
            .order_by(Listing.published_at.desc())
            .limit(SELLER_ADS)
        )
    ).all()
    return {
        "id": seller.id,
        "name": seller.name or (seller.email.split("@")[0] if seller.email else "—"),
        "since": seller.created_at,
        "rating": average,
        "reviews_count": count,
        "reviews": await about(session, seller_id),
        "listings": await public_cards(session, list(rows), lang),
    }
