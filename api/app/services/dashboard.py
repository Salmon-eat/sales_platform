"""Admin dashboard: traffic from the anonymous site events, work from applications and listings.

Traffic numbers (visitors, funnel, sources, ad links) come from analytics_events, so they agree with
each other; the managers' queue (new, in progress, stuck) comes from the applications table.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TZ = "Europe/Madrid"
STALE_AFTER = timedelta(hours=48)
LOADTEST = """NOT (l.contact @> '{"_loadtest": true}')"""
# site events of real visits; link_click rows come from the /go redirect and carry no visitor
VISITS = "created_at >= :start AND created_at < :end AND type <> 'link_click'"


def _name(column: str) -> str:
    return f"coalesce({column}->>:lang, {column}->>'es')"


LISTING_TITLE = """(SELECT t.title FROM listing_translations t WHERE t.listing_id = l.id
    ORDER BY (t.lang = :lang) DESC, (t.lang = l.original_lang) DESC LIMIT 1)"""


async def _rows(session: AsyncSession, sql: str, **params: Any) -> list[dict[str, Any]]:
    result = await session.execute(text(sql), params)
    return [dict(r._mapping) for r in result]


async def _one(session: AsyncSession, sql: str, **params: Any) -> dict[str, Any]:
    rows = await _rows(session, sql, **params)
    return rows[0] if rows else {}


async def _traffic(session: AsyncSession, start: datetime, end: datetime) -> dict[str, Any]:
    return await _one(
        session,
        f"""
        WITH s AS (
            SELECT session, min(visitor) AS visitor,
                   coalesce(sum(duration_ms) FILTER (WHERE type = 'page_leave'), 0) AS dur,
                   count(*) FILTER (WHERE type = 'page_view') AS views,
                   bool_or(type = 'listing_view') AS viewed_job,
                   bool_or(type = 'apply_open') AS opened,
                   bool_or(type = 'apply_sent') AS sent
            FROM analytics_events WHERE {VISITS} GROUP BY session
        )
        SELECT count(DISTINCT visitor) AS visitors,
               count(*) AS sessions,
               coalesce(sum(views), 0)::int AS pageviews,
               coalesce(round(avg(dur) / 1000), 0)::int AS avg_session_sec,
               count(*) FILTER (WHERE views <= 1 AND NOT viewed_job AND NOT opened AND NOT sent) AS bounces,
               count(*) FILTER (WHERE viewed_job) AS viewed_job,
               count(*) FILTER (WHERE opened) AS opened,
               count(*) FILTER (WHERE sent) AS sent
        FROM s
        """,
        start=start,
        end=end,
    )


async def build_dashboard(session: AsyncSession, days: int, lang: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    if days == 1:
        # "today" in Madrid, compared with yesterday
        local_midnight = await session.scalar(
            text(f"SELECT date_trunc('day', now() AT TIME ZONE '{TZ}') AT TIME ZONE '{TZ}'")
        )
        start = local_midnight
        prev_start, prev_end = start - timedelta(days=1), start
    else:
        start = now - timedelta(days=days)
        prev_start, prev_end = start - timedelta(days=days), start
    p = {"start": start, "end": now, "lang": lang}

    traffic = await _traffic(session, start, now)
    traffic_prev = await _traffic(session, prev_start, prev_end)

    daily = await _rows(
        session,
        f"""
        WITH d AS (
            SELECT generate_series(
                date_trunc('day', CAST(:start AS timestamptz) AT TIME ZONE '{TZ}'),
                date_trunc('day', CAST(:end AS timestamptz) AT TIME ZONE '{TZ}'),
                interval '1 day')::date AS day
        ),
        e AS (
            SELECT (created_at AT TIME ZONE '{TZ}')::date AS day,
                   count(DISTINCT visitor) AS visitors,
                   count(DISTINCT session) FILTER (WHERE type = 'apply_sent') AS applications
            FROM analytics_events WHERE {VISITS} GROUP BY 1
        )
        SELECT d.day, coalesce(e.visitors, 0) AS visitors, coalesce(e.applications, 0) AS applications
        FROM d LEFT JOIN e USING (day) ORDER BY d.day
        """,
        start=start,
        end=now,
    )

    sources = await _rows(
        session,
        f"""
        SELECT source, count(DISTINCT visitor) AS visitors,
               count(DISTINCT session) FILTER (WHERE type = 'apply_sent') AS applications
        FROM analytics_events WHERE {VISITS}
        GROUP BY source ORDER BY visitors DESC LIMIT 12
        """,
        start=start,
        end=now,
    )

    campaigns = await _rows(
        session,
        f"""
        SELECT tl.id, tl.code, tl.name, tl.channel, tl.cost, tl.is_active,
               coalesce(c.clicks, 0) AS clicks, coalesce(v.visitors, 0) AS visitors,
               coalesce(v.applications, 0) AS applications
        FROM tracked_links tl
        LEFT JOIN (
            SELECT campaign, count(*) AS clicks FROM analytics_events
            WHERE type = 'link_click' AND created_at >= :start AND created_at < :end GROUP BY campaign
        ) c ON c.campaign = tl.code
        LEFT JOIN (
            SELECT campaign, count(DISTINCT visitor) AS visitors,
                   count(DISTINCT session) FILTER (WHERE type = 'apply_sent') AS applications
            FROM analytics_events WHERE {VISITS} AND campaign IS NOT NULL GROUP BY campaign
        ) v ON v.campaign = tl.code
        WHERE tl.is_active OR c.clicks > 0 OR v.visitors > 0
        ORDER BY applications DESC, visitors DESC, clicks DESC LIMIT 10
        """,
        start=start,
        end=now,
    )

    devices = await _rows(
        session,
        f"SELECT device AS key, count(DISTINCT visitor) AS visitors FROM analytics_events "
        f"WHERE {VISITS} GROUP BY device ORDER BY visitors DESC",
        start=start,
        end=now,
    )
    langs = await _rows(
        session,
        f"SELECT coalesce(lang, '—') AS key, count(DISTINCT visitor) AS visitors FROM analytics_events "
        f"WHERE {VISITS} GROUP BY 1 ORDER BY visitors DESC",
        start=start,
        end=now,
    )

    landing = await _rows(
        session,
        f"""
        SELECT path, count(*) AS sessions FROM (
            SELECT DISTINCT ON (session) session, path FROM analytics_events
            WHERE {VISITS} AND type = 'page_view' ORDER BY session, created_at
        ) x GROUP BY path ORDER BY sessions DESC LIMIT 8
        """,
        start=start,
        end=now,
    )
    # where visits that ended without an application stopped
    exits = await _rows(
        session,
        f"""
        WITH sent AS (
            SELECT DISTINCT session FROM analytics_events WHERE {VISITS} AND type = 'apply_sent'
        )
        SELECT path, count(*) AS sessions FROM (
            SELECT DISTINCT ON (session) session, path FROM analytics_events
            WHERE {VISITS} AND type = 'page_view' AND session NOT IN (SELECT session FROM sent)
            ORDER BY session, created_at DESC
        ) x GROUP BY path ORDER BY sessions DESC LIMIT 8
        """,
        start=start,
        end=now,
    )

    listing_stats = f"""
        WITH v AS (
            SELECT listing_id, count(DISTINCT session) AS views FROM analytics_events
            WHERE {VISITS} AND type = 'listing_view' AND listing_id IS NOT NULL GROUP BY listing_id
        ), a AS (
            SELECT listing_id, count(DISTINCT session) AS applications FROM analytics_events
            WHERE {VISITS} AND type = 'apply_sent' AND listing_id IS NOT NULL GROUP BY listing_id
        )
        SELECT l.id, l.status, {LISTING_TITLE} AS title, v.views, coalesce(a.applications, 0) AS applications,
               (l.salary_min IS NULL AND l.salary_max IS NULL) AS no_salary
        FROM v JOIN listings l ON l.id = v.listing_id LEFT JOIN a ON a.listing_id = v.listing_id
    """
    top_listings = await _rows(session, f"{listing_stats} ORDER BY v.views DESC LIMIT 10", **p)
    unanswered_listings = await _rows(
        session,
        f"{listing_stats} WHERE coalesce(a.applications, 0) = 0 AND v.views >= 5 "
        f"AND l.status = 'active' ORDER BY v.views DESC LIMIT 8",
        **p,
    )

    searches = await _rows(
        session,
        f"""
        SELECT lower(trim(props->>'q')) AS q, count(*) AS count FROM analytics_events
        WHERE {VISITS} AND type = 'search' AND coalesce(trim(props->>'q'), '') <> ''
        GROUP BY 1 ORDER BY count DESC LIMIT 10
        """,
        start=start,
        end=now,
    )
    misses = await _rows(
        session,
        "SELECT q, lang, hits FROM search_misses WHERE last_seen >= :start ORDER BY hits DESC LIMIT 15",
        start=start,
    )

    # ---------- the managers' queue (real applications from the site; the bot's live in Telegram) ----------
    work = await _one(
        session,
        """
        SELECT count(*) FILTER (WHERE status = 'new') AS new,
               count(*) FILTER (WHERE status = 'in_progress') AS in_progress,
               count(*) FILTER (WHERE status IN ('new', 'in_progress') AND updated_at < :stale) AS stale,
               count(*) FILTER (WHERE created_at >= :start) AS period,
               count(*) FILTER (WHERE created_at >= :prev_start AND created_at < :start) AS period_prev,
               count(*) FILTER (WHERE created_at >= :start AND listing_id IS NOT NULL) AS responses,
               count(*) FILTER (WHERE created_at >= :start AND listing_id IS NULL) AS callbacks,
               count(*) FILTER (WHERE created_at >= :start AND status = 'done') AS done,
               count(*) FILTER (WHERE created_at >= :start AND status = 'rejected') AS rejected
        FROM applications WHERE source <> 'bot'
        """,
        start=start,
        prev_start=prev_start,
        stale=now - STALE_AFTER,
    )
    oldest_new = await _rows(
        session,
        """
        SELECT id, name, status, updated_at FROM applications
        WHERE source <> 'bot' AND status IN ('new', 'in_progress') AND updated_at < :stale
        ORDER BY updated_at LIMIT 5
        """,
        stale=now - STALE_AFTER,
    )
    by_category = await _rows(
        session,
        f"""
        SELECT {_name("c.name")} AS name, count(*) AS count
        FROM applications a
        LEFT JOIN listings l ON l.id = a.listing_id
        JOIN categories c ON c.id = coalesce(a.category_id, l.category_id)
        WHERE a.created_at >= :start GROUP BY 1 ORDER BY count DESC LIMIT 8
        """,
        **p,
    )
    by_city = await _rows(
        session,
        f"""
        SELECT {_name("loc.names")} AS name, count(*) AS count
        FROM applications a
        LEFT JOIN listings l ON l.id = a.listing_id
        JOIN locations loc ON loc.id = coalesce(a.location_id, l.location_id)
        WHERE a.created_at >= :start GROUP BY 1 ORDER BY count DESC LIMIT 8
        """,
        **p,
    )

    listings = await _one(
        session,
        f"""
        SELECT count(*) FILTER (WHERE l.status = 'active') AS active,
               count(*) FILTER (WHERE l.status = 'active' AND l.salary_min IS NULL AND l.salary_max IS NULL)
                   AS active_no_salary,
               count(*) FILTER (WHERE l.status = 'active' AND l.expires_at < :soon) AS expiring,
               count(*) FILTER (WHERE l.status = 'draft') AS drafts,
               count(*) FILTER (WHERE l.status = 'active'
                   AND NOT EXISTS (SELECT 1 FROM listing_translations t
                                   WHERE t.listing_id = l.id AND t.lang = 'uk')) AS active_no_uk,
               count(*) FILTER (WHERE l.status = 'active'
                   AND NOT EXISTS (SELECT 1 FROM listing_translations t
                                   WHERE t.listing_id = l.id AND t.lang = 'ru')) AS active_no_ru
        FROM listings l WHERE {LOADTEST}
        """,
        soon=now + timedelta(days=3),
    )

    return {
        "days": days,
        "start": start,
        "end": now,
        "traffic": traffic,
        "traffic_prev": traffic_prev,
        "daily": daily,
        "sources": sources,
        "campaigns": campaigns,
        "devices": devices,
        "langs": langs,
        "landing": landing,
        "exits": exits,
        "top_listings": top_listings,
        "unanswered_listings": unanswered_listings,
        "searches": searches,
        "misses": misses,
        "work": work,
        "stale": oldest_new,
        "by_category": by_category,
        "by_city": by_city,
        "listings": listings,
    }
