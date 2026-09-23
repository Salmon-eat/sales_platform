"""Demo ads for the new sections, so the board is not empty before real people post.

They go through save_listing(), the same path the posting form uses, so the seed is validated like a real
ad. Every one of them carries a mark in `contact`, which is how delete-demo-ads finds them again.
"""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Listing, Location, Section, User, UserRole
from app.schemas.listing import ListingIn
from app.services.listings import save_listing

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "ads_demo.json"
MARK = {"_demo_ad": True}


def demo_ads_condition():
    return Listing.contact.contains(MARK)


async def seed_demo_ads(session: AsyncSession) -> int:
    author = await session.scalar(
        select(User).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1)
    )
    if author is None:
        raise RuntimeError("create an admin first: python -m app.cli create-staff ...")
    if await session.scalar(select(Listing.id).where(demo_ads_condition()).limit(1)):
        return 0

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    created = 0
    for index, item in enumerate(data["ads"]):
        # the section matters: slugs like "limpieza" exist both in jobs and in services
        category_id = await session.scalar(
            select(Category.id)
            .join(Section, Section.id == Category.section_id)
            .where(
                Section.key == item["section"],
                Category.slug["es"].astext == item["category"],
                Category.is_enabled.is_(True),
            )
        )
        if category_id is None:
            raise RuntimeError(
                f"category {item['section']}/{item['category']} not found; run seed-taxonomy first"
            )
        location_id = await session.scalar(
            select(Location.id).where(Location.slug == item["city"], Location.level == "municipio")
        )
        if location_id is None:
            raise RuntimeError(f"location {item['city']} not found; run import-locations first")

        payload = ListingIn(
            category_id=category_id,
            location_scope="local",
            location_id=location_id,
            price=item.get("price"),
            price_period=item.get("price_period"),
            price_kind=item.get("price_kind", "fixed"),
            attributes=item.get("attributes", {}),
            source="employer",
            employer_name="Citobazar demo",
            translations=[{"lang": lang, **text} for lang, text in item["translations"].items()],
        )
        listing = await save_listing(session, author, payload)
        listing.contact = MARK
        listing.status = "active"
        # spread them over the last few days so "newest" looks natural
        listing.published_at = now - timedelta(hours=index * 7 + random.randint(0, 5))
        listing.expires_at = now + timedelta(days=30)
        created += 1

    await session.commit()
    return created


async def delete_demo_ads(session: AsyncSession) -> int:
    result = await session.execute(delete(Listing).where(demo_ads_condition()))
    await session.commit()
    return result.rowcount or 0
