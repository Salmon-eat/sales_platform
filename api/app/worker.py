"""Background jobs (APScheduler, as in Navtiro).

    python -m app.worker

Stage 2: auto-expire listings. Stage 4 adds seo_pages recount, stage 7 backups/alerts.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.core.db import SessionLocal, engine
from app.core.redis import redis
from app.seo.counts import recount_seo_pages
from app.services.cache import bump_cache_version
from app.services.gdpr import anonymize_expired
from app.services.listings import expire_listings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")

EXPIRE_EVERY_MINUTES = 10
SEO_RECOUNT_EVERY_MINUTES = 60


async def expire_job() -> None:
    try:
        async with SessionLocal() as session:
            count = await expire_listings(session)
    except Exception:
        # e.g. the database is not migrated yet; the next run retries
        logger.exception("expire_listings failed")
        return
    if count:
        await bump_cache_version(redis)
        logger.info("expired %s listings", count)


async def seo_recount_job() -> None:
    try:
        async with SessionLocal() as session:
            stats = await recount_seo_pages(session)
        logger.info("seo_pages recounted: %s", stats)
    except Exception:
        logger.exception("seo recount failed")


async def analytics_cleanup_job() -> None:
    """Site events are kept 13 months: enough to compare with the same month last year."""
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                text("DELETE FROM analytics_events WHERE created_at < now() - interval '13 months'")
            )
            await session.commit()
        if result.rowcount:
            logger.info("deleted %s old analytics events", result.rowcount)
    except Exception:
        logger.exception("analytics cleanup failed")


async def gdpr_job() -> None:
    """Closed applications older than the retention period lose their personal data (admin spec §9)."""
    try:
        async with SessionLocal() as session:
            count = await anonymize_expired(session)
        if count:
            logger.info("anonymized %s old applications", count)
    except Exception:
        logger.exception("gdpr anonymization failed")


async def main() -> None:
    scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
    scheduler.add_job(
        expire_job, "interval", minutes=EXPIRE_EVERY_MINUTES, id="expire_listings", coalesce=True
    )
    scheduler.add_job(
        seo_recount_job, "interval", minutes=SEO_RECOUNT_EVERY_MINUTES, id="seo_recount", coalesce=True
    )
    scheduler.add_job(analytics_cleanup_job, "cron", hour=4, id="analytics_cleanup", coalesce=True)
    scheduler.add_job(gdpr_job, "cron", hour=4, minute=30, id="gdpr_anonymize", coalesce=True)
    scheduler.start()
    logger.info("worker started")
    await expire_job()  # catch up right after a restart
    await seo_recount_job()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
