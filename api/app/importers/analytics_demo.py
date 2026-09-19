"""Demo traffic for the dashboard (local only): 60 days of visits, a few ad links.

Events are marked props._demo, links use the DEMO_LINKS codes; delete_demo_analytics removes both.
No applications are created: the managers' queue shows only real ones.
"""

import random
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AnalyticsEvent, Category, Listing, Section, TrackedLink
from app.seo.paths import listing_path

URL_PREFIX = {"es": "es", "en": "en", "uk": "ua", "ru": "ru"}
LANG_WEIGHTS = {"uk": 45, "ru": 30, "es": 17, "en": 8}
SOURCE_WEIGHTS = {
    "direct": 30,
    "google": 28,
    "instagram": 12,
    "facebook": 9,
    "telegram": 8,
    "tiktok": 5,
    "bing": 2,
}

DEMO_LINKS = [
    # code, name, channel, section key or None for home, cost, share of visits, conversion boost
    ("olena-insta-sep", "Olena Travel · Instagram", "blogger", "empleo", 150, 0.06, 1.4),
    ("tiktok-camioneros", "TikTok: vídeo camioneros", "tiktok", "empleo", 90, 0.05, 0.5),
    ("fb-grupa-valencia", "Facebook: група «Українці у Валенсії»", "facebook", None, 0, 0.04, 1.1),
    ("tg-kanal-ispania", "Telegram: канал «Іспанія для своїх»", "telegram", None, 60, 0.03, 0.9),
]
SEARCHES = [
    "водій CE",
    "camarero",
    "кухар",
    "без мови",
    "з житлом",
    "almacén",
    "limpieza",
    "курси код 95",
    "NIE",
    "conductor",
    "прибирання",
    "Валенсія",
    "мойщик",
    "сварщик",
    "Madrid",
]


def _id() -> str:
    return secrets.token_hex(8)


async def _paths(session: AsyncSession) -> tuple[dict, list[tuple[int, dict[str, str]]]]:
    sections = (await session.scalars(select(Section).where(Section.is_enabled))).all()
    by_key = {s.key: s for s in sections}
    categories = (
        await session.scalars(select(Category).where(Category.is_enabled, Category.parent_id.is_(None)))
    ).all()
    pages: dict[str, list[str]] = {lang: [""] for lang in URL_PREFIX}
    for s in sections:
        for lang in URL_PREFIX:
            pages[lang].append(s.slug[lang])
    for c in categories[:20]:
        section = next((s for s in sections if s.id == c.section_id), None)
        if section is None:
            continue
        for lang in URL_PREFIX:
            pages[lang].append(f"{section.slug[lang]}/{c.slug[lang]}")

    listings = (
        await session.scalars(
            select(Listing)
            .where(Listing.status == "active", ~Listing.contact.contains({"_loadtest": True}))
            .options(selectinload(Listing.translations))
            .limit(60)
        )
    ).all()
    cards = []
    for x in listings:
        section = next((s for s in sections if s.id == x.section_id), None)
        texts = {t.lang: t for t in x.translations}
        if section is None or not texts:
            continue
        fallback = texts.get(x.original_lang) or next(iter(texts.values()))
        cards.append(
            (
                x.id,
                {
                    lang: listing_path(section.slug[lang], lang, (texts.get(lang) or fallback).slug, x.id)
                    for lang in URL_PREFIX
                },
            )
        )
    return {"pages": pages, "sections": by_key}, cards


def _url(lang: str, path: str) -> str:
    return f"/{URL_PREFIX[lang]}/{path}".rstrip("/")


async def seed_demo_analytics(session: AsyncSession, days: int = 60, visits_per_day: int = 110) -> int:
    await delete_demo_analytics(session)
    rng = random.Random(42)
    site, cards = await _paths(session)
    if not cards:
        return 0
    popular = cards[: max(3, len(cards) // 3)]

    for code, name, channel, section_key, cost, *_ in DEMO_LINKS:
        section = site["sections"].get(section_key) if section_key else None
        target = _url("uk", section.slug["uk"]) if section else "/ua"
        session.add(TrackedLink(code=code, name=name, channel=channel, target_path=target, cost=cost or None))

    now = datetime.now(UTC)
    events: list[AnalyticsEvent] = []
    visitors = [_id() for _ in range(days * visits_per_day // 2)]  # some people come back

    def add(t: datetime, v: str, s: str, lang: str, device: str, source: str, campaign: str | None, **kw):
        props = kw.pop("props", {})
        events.append(
            AnalyticsEvent(
                created_at=t,
                visitor=v,
                session=s,
                lang=lang,
                device=device,
                source=source,
                campaign=campaign,
                props={**props, "_demo": True},
                **kw,
            )
        )

    for day in range(days, -1, -1):
        base = now - timedelta(days=day)
        growth = 0.6 + 0.4 * (days - day) / days  # traffic grows over the month
        weekend = 0.75 if base.weekday() >= 5 else 1
        for _ in range(int(visits_per_day * growth * weekend * rng.uniform(0.85, 1.15))):
            t = base.replace(
                hour=rng.choice(range(7, 24)), minute=rng.randrange(60), second=rng.randrange(60)
            )
            if t > now:
                continue
            lang = rng.choices(list(LANG_WEIGHTS), list(LANG_WEIGHTS.values()))[0]
            device = rng.choices(["mobile", "desktop", "tablet"], [74, 22, 4])[0]
            link = next((x for x in DEMO_LINKS if rng.random() < x[5]), None)
            if link:
                source, campaign, boost = link[2], link[0], link[6]
                add(
                    t - timedelta(seconds=3),
                    "",
                    "",
                    None,
                    "desktop",
                    source,
                    campaign,
                    type="link_click",
                    path="/",
                )
            else:
                source = rng.choices(list(SOURCE_WEIGHTS), list(SOURCE_WEIGHTS.values()))[0]
                campaign, boost = None, 1.0
            v, s = rng.choice(visitors), _id()
            pages = site["pages"][lang]
            path = _url(lang, rng.choice(pages[:4]) if rng.random() < 0.7 else rng.choice(pages))

            # ~42% leave after the first page
            steps = 1 if rng.random() < 0.42 else rng.randint(2, 7)
            for step in range(steps):
                add(t, v, s, lang, device, source, campaign, type="page_view", path=path)
                stay = int(rng.expovariate(1 / (25_000 if step == 0 else 55_000)))
                listing_id = None
                if rng.random() < 0.12:
                    add(
                        t + timedelta(seconds=4),
                        v,
                        s,
                        lang,
                        device,
                        source,
                        campaign,
                        type="search",
                        path=path,
                        props={"q": rng.choice(SEARCHES)},
                    )
                if step and rng.random() < 0.55:
                    listing_id, card = rng.choice(popular if rng.random() < 0.7 else cards)
                    path = _url(lang, card[lang])
                    add(t, v, s, lang, device, source, campaign, type="page_view", path=path)
                    add(
                        t,
                        v,
                        s,
                        lang,
                        device,
                        source,
                        campaign,
                        type="listing_view",
                        path=path,
                        listing_id=listing_id,
                    )
                    # the first two popular jobs get views, people open the form but nobody sends it
                    weak = listing_id in (popular[0][0], popular[1][0])
                    if rng.random() < 0.28 * boost * (0.4 if weak else 1):
                        add(
                            t + timedelta(seconds=20),
                            v,
                            s,
                            lang,
                            device,
                            source,
                            campaign,
                            type="apply_open",
                            path=path,
                            listing_id=listing_id,
                        )
                        if not weak and rng.random() < 0.45:
                            add(
                                t + timedelta(seconds=90),
                                v,
                                s,
                                lang,
                                device,
                                source,
                                campaign,
                                type="apply_sent",
                                path=path,
                                listing_id=listing_id,
                            )
                            break
                elif step == 0 and rng.random() < 0.03 * boost:
                    add(
                        t + timedelta(seconds=15),
                        v,
                        s,
                        lang,
                        device,
                        source,
                        campaign,
                        type="apply_open",
                        path=path,
                    )
                    if rng.random() < 0.5:
                        add(
                            t + timedelta(seconds=80),
                            v,
                            s,
                            lang,
                            device,
                            source,
                            campaign,
                            type="apply_sent",
                            path=path,
                        )
                        break
                add(
                    t + timedelta(milliseconds=stay),
                    v,
                    s,
                    lang,
                    device,
                    source,
                    campaign,
                    type="page_leave",
                    path=path,
                    duration_ms=min(stay, 30 * 60 * 1000),
                    listing_id=listing_id,
                )
                t += timedelta(milliseconds=stay + 2000)
                if not listing_id:
                    path = _url(lang, rng.choice(pages))

    session.add_all(events)
    await session.commit()
    return len(events)


async def delete_demo_analytics(session: AsyncSession) -> int:
    result = await session.execute(delete(AnalyticsEvent).where(AnalyticsEvent.props.has_key("_demo")))
    links = await session.execute(delete(TrackedLink).where(TrackedLink.code.in_([x[0] for x in DEMO_LINKS])))
    # link clicks of the demo links carry the _demo mark too
    await session.commit()
    return result.rowcount + links.rowcount
