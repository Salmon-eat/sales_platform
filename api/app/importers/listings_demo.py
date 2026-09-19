"""Demo listings for development. Uses save_listing(), so the seed is validated like the admin form."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Listing, Location, User, UserRole
from app.schemas.listing import ListingIn
from app.services.listings import save_listing

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "listings_demo.json"


async def seed_demo_listings(session: AsyncSession) -> int:
    if await session.scalar(select(func.count()).select_from(Listing)):
        return 0
    author = await session.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1))
    if author is None:
        raise RuntimeError("create an admin first: python -m app.cli create-staff ...")

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    created = 0
    for item in data["listings"]:
        category_id = await session.scalar(
            select(Category.id).where(Category.slug["es"].astext == item["category"])
        )
        location_id = None
        if item["city"]:
            location_id = await session.scalar(
                select(Location.id).where(Location.slug == item["city"], Location.level == "municipio")
            )
            if location_id is None:
                raise RuntimeError(f"location {item['city']} not found; run import-locations first")

        payload = ListingIn(
            category_id=category_id,
            location_scope="local" if item["city"] else "spain_wide",
            location_id=location_id,
            translations=[{"lang": lang, **text} for lang, text in item["translations"].items()],
            **{
                k: item[k]
                for k in (
                    "salary_min",
                    "salary_max",
                    "salary_period",
                    "housing",
                    "no_language",
                    "no_experience",
                    "schedule",
                    "contract",
                    "attributes",
                    "source",
                    "employer_name",
                    "is_pinned",
                )
                if k in item
            },  # fmt: skip
        )
        listing = await save_listing(session, author, payload)

        if item["status"] != "draft":
            published = now - timedelta(hours=item.get("hours_ago", 1))
            listing.published_at = published
            listing.expires_at = now + timedelta(days=item.get("expires_in_days", 30))
            listing.status = item["status"]
            await session.commit()
        created += 1
    return created
