"""Management commands.

python -m app.cli create-staff --email admin@example.com [--role manager]
python -m app.cli seed-taxonomy
python -m app.cli import-locations [--download]
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal, engine
from app.core.redis import redis
from app.importers.ads_demo import delete_demo_ads, seed_demo_ads
from app.importers.analytics_demo import delete_demo_analytics, seed_demo_analytics
from app.importers.demo_extras import delete_demo_extras, seed_demo_extras
from app.importers.content import seed_content
from app.importers.listings_demo import seed_demo_listings
from app.importers.loadtest_data import create_fake_listings, delete_fake_listings
from app.importers.locations import import_locations
from app.importers.taxonomy import seed_taxonomy
from app.importers.top_demo import seed_demo_top
from app.models import User, UserRole
from app.search.spelling import refresh as refresh_search_words
from app.seo.counts import recount_seo_pages
from app.services.cache import bump_cache_version
from app.services.listings import expire_listings
from app.services.synonyms import collect as collect_synonyms


async def create_staff(email: str, role: UserRole) -> None:
    """Whitelist an email (admin spec §1): the person signs in with Google; there are no passwords."""
    email = email.lower()
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email)
            session.add(user)
        user.role = role
        user.is_active = True
        await session.commit()
    print(f"{role} {email} can sign in with Google")


async def seed_taxonomy_cmd() -> None:
    async with SessionLocal() as session:
        report = await seed_taxonomy(session)
    await bump_cache_version(redis, taxonomy=True)
    print(
        f"taxonomy: {report.sections} sections, {report.categories} categories, "
        f"{report.attributes} attributes, {report.slang_words} words from search_slang.json"
    )
    for warning in report.warnings:
        print(f"  ! {warning}")


async def import_locations_cmd(download: bool) -> None:
    async with SessionLocal() as session:
        report = await import_locations(session, download=download)
    await bump_cache_version(redis, taxonomy=True)

    print(
        f"locations: {report.comunidades} comunidades, {report.provincias} provincias, "
        f"{report.municipios} municipios, {report.localidades} localidades (villages)"
    )
    print(f"coordinates: {report.coords_from_place} from town centre, {report.coords_from_adm3} from ADM3")
    for title, items in (
        ("matched by name (no INE code in GeoNames)", report.matched_by_name),
        ("approximate coordinates (verify)", report.approximate_coords),
        ("not found in GeoNames (skipped)", report.without_geonames),
        ("slug collisions resolved", report.slug_collisions),
        ("override warnings", report.override_warnings),
    ):
        print(f"{title}: {len(items)}")
        for item in items[:40]:
            print(f"  {item}")

    print("top municipalities (check uk/ru names):")
    for row in report.top:
        names = " | ".join(f"{lang}={row.names.get(lang, '—')}" for lang in ("es", "en", "uk", "ru"))
        print(f"  {row.ine_code} {row.slug:<28} {row.population or 0:>8}  {names}")


async def seed_listings_cmd() -> None:
    async with SessionLocal() as session:
        created = await seed_demo_listings(session)
    await bump_cache_version(redis)
    print(f"demo listings: {created} created" if created else "listings already exist, skipping")


async def seed_ads_cmd() -> None:
    """Demo ads in the new sections (real estate, motor, items...), so the board looks alive."""
    async with SessionLocal() as session:
        created = await seed_demo_ads(session)
    await bump_cache_version(redis)
    print(f"demo ads: {created} created" if created else "demo ads already there, skipping")


async def delete_ads_cmd() -> None:
    async with SessionLocal() as session:
        removed = await delete_demo_ads(session)
    await bump_cache_version(redis)
    print(f"demo ads removed: {removed}")


async def seed_extras_cmd() -> None:
    """Firms, CVs, reviews, conversations, orders and articles: a site that looks used."""
    async with SessionLocal() as session:
        made = await seed_demo_extras(session)
    await bump_cache_version(redis)
    print(f"demo extras: {made}" if made else "demo extras already there, skipping")


async def delete_extras_cmd() -> None:
    async with SessionLocal() as session:
        removed = await delete_demo_extras(session)
    await bump_cache_version(redis)
    print(f"demo extras removed: {removed}" if removed else "nothing to remove")


async def top_cmd() -> None:
    """A few paid "top" ads in every section, to see how they look."""
    async with SessionLocal() as session:
        made = await seed_demo_top(session)
    await bump_cache_version(redis)
    print(f"top ads per section: {made}")


async def search_words_cmd() -> None:
    """Rebuild the site's own vocabulary: what a misspelled word is repaired against."""
    async with SessionLocal() as session:
        count = await refresh_search_words(session)
    print(f"search vocabulary: {count} words")


async def learn_words_cmd() -> None:
    """What visitors searched for in vain, and where they went instead (the worker does it nightly)."""
    async with SessionLocal() as session:
        written, applied = await collect_synonyms(session)
    await bump_cache_version(redis, taxonomy=True)
    print(f"search words: {applied} added on their own, {written} waiting for a decision")


async def expire_listings_cmd() -> None:
    async with SessionLocal() as session:
        count = await expire_listings(session)
    await bump_cache_version(redis)
    print(f"expired {count} listings")


async def fake_listings_cmd(count: int, with_photos: bool) -> None:
    async with SessionLocal() as session:
        created = await create_fake_listings(session, count, with_photos=with_photos)
    await bump_cache_version(redis)
    print(f"created {created} fake listings (marked in contact._loadtest, removed by delete-fake-listings)")


async def delete_fake_listings_cmd() -> None:
    async with SessionLocal() as session:
        removed = await delete_fake_listings(session)
    await bump_cache_version(redis)
    print(f"deleted {removed} fake listings")


async def recount_seo_cmd() -> None:
    async with SessionLocal() as session:
        stats = await recount_seo_pages(session)
    print(f"seo_pages: {stats}")


async def seed_content_cmd() -> None:
    async with SessionLocal() as session:
        count = await seed_content(session)
    print(f"content blocks: {count}")


async def seed_demo_analytics_cmd() -> None:
    async with SessionLocal() as session:
        count = await seed_demo_analytics(session)
    print(f"demo analytics: {count} events (removed by delete-demo-analytics)")


async def delete_demo_analytics_cmd() -> None:
    async with SessionLocal() as session:
        count = await delete_demo_analytics(session)
    print(f"deleted {count} demo events and links")


async def run(args: argparse.Namespace) -> None:
    try:
        match args.command:
            case "create-staff":
                await create_staff(args.email, UserRole(args.role))
            case "seed-taxonomy":
                await seed_taxonomy_cmd()
            case "import-locations":
                await import_locations_cmd(args.download)
            case "seed-listings":
                await seed_listings_cmd()
            case "seed-demo-ads":
                await seed_ads_cmd()
            case "delete-demo-ads":
                await delete_ads_cmd()
            case "seed-demo-extras":
                await seed_extras_cmd()
            case "delete-demo-extras":
                await delete_extras_cmd()
            case "seed-demo-top":
                await top_cmd()
            case "refresh-search-words":
                await search_words_cmd()
            case "learn-search-words":
                await learn_words_cmd()
            case "expire-listings":
                await expire_listings_cmd()
            case "seed-fake-listings":
                await fake_listings_cmd(args.count, not args.no_photos)
            case "delete-fake-listings":
                await delete_fake_listings_cmd()
            case "recount-seo":
                await recount_seo_cmd()
            case "seed-content":
                await seed_content_cmd()
            case "seed-demo-analytics":
                await seed_demo_analytics_cmd()
            case "delete-demo-analytics":
                await delete_demo_analytics_cmd()
    finally:
        await redis.aclose()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    staff = sub.add_parser("create-staff", help="whitelist an email as manager/admin (Google sign-in)")
    staff.add_argument("--email", required=True)
    staff.add_argument("--role", choices=[UserRole.ADMIN, UserRole.MANAGER], default=UserRole.ADMIN)

    sub.add_parser("seed-taxonomy", help="create/update sections, categories and attributes from seeds/")

    locations = sub.add_parser("import-locations", help="import Spain locations from INE + GeoNames")
    locations.add_argument("--download", action="store_true", help="download missing source files")

    sub.add_parser("seed-listings", help="create demo listings (only into an empty table)")
    sub.add_parser("seed-demo-ads", help="demo ads for the classifieds sections (flats, cars, items...)")
    sub.add_parser("delete-demo-ads", help="remove those demo ads")
    sub.add_parser("seed-demo-extras", help="firms, CVs, reviews, chats, orders and articles (local only)")
    sub.add_parser("delete-demo-extras", help="remove all of that demo data")
    sub.add_parser("seed-demo-top", help="put 1-3 existing ads of every section on paid top (local only)")
    sub.add_parser("refresh-search-words", help="rebuild the words a search typo is repaired against")
    sub.add_parser(
        "learn-search-words", help="turn fruitless searches into category words (the worker does it nightly)"
    )
    sub.add_parser(
        "expire-listings", help="mark listings past expires_at as expired (the worker does it every 10 min)"
    )

    fake = sub.add_parser("seed-fake-listings", help="bulk fake listings for the load test, all sections")
    fake.add_argument("--count", type=int, default=10_000)
    fake.add_argument("--no-photos", action="store_true", help="skip the placeholder pictures")
    sub.add_parser("delete-fake-listings", help="remove the load-test listings and their pictures")
    sub.add_parser("recount-seo", help="recount seo_pages (the worker does it hourly)")
    sub.add_parser("seed-content", help="static page texts from seeds/content.json")
    sub.add_parser("seed-demo-analytics", help="60 days of demo traffic for the dashboard (local only)")
    sub.add_parser("delete-demo-analytics", help="remove the demo traffic and demo ad links")

    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
