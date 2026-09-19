"""Fake listings for the load test (spec §11, stage 3: 10k listings, p95 of list+facets < 300 ms).

All rows carry contact = {"_loadtest": true} (never shown on the site) so they can be removed with
delete-fake-listings; the employer names look real because demo screens are shown to people.
Triggers are disabled during the bulk insert and the search documents are rebuilt once at the end.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slug import slugify
from app.models import AttributeDefinition, Category, Listing, ListingTranslation, Location, Section
from app.services.listing_rules import monthly_min

MARKER = {"_loadtest": True}  # in listings.contact
BATCH = 1000
COMPANIES = [
    "Transportes Levante", "Logística Ibérica", "Hostelería Mediterránea", "Grupo Costa Sol",
    "Agrícola del Sur", "Construcciones Norte", "Limpiezas Brillo", "Almacenes Centro",
    "Cuidados en Casa", "Frutas Huerta Viva",
]  # fmt: skip


def is_fake():  # noqa: ANN201
    return Listing.contact.contains(MARKER)


ADJECTIVES = {
    "es": ["urgente", "con experiencia", "sin experiencia", "temporada", "fin de semana", "turno de noche"],
    "uk": ["терміново", "з досвідом", "без досвіду", "сезон", "вихідні", "нічна зміна"],
}
BODY = {
    "es": "Buscamos personal para incorporación inmediata. Contrato, alta en la Seguridad Social y buen ambiente.",  # noqa: E501
    "uk": "Шукаємо працівників із виходом одразу. Офіційне оформлення, стабільні виплати й житло за потреби.",
}


def fake_section_tags(
    rng: random.Random, tags: list[AttributeDefinition], section_id: int
) -> dict[str, object]:
    """Section tags (for students, documents...) on roughly every fourth listing each."""
    out: dict[str, object] = {}
    for tag in tags:
        if tag.section_id != section_id or rng.random() > 0.25:
            continue
        values = [o["value"] for o in tag.options]
        if tag.type == "bool":
            out[tag.key] = True
        elif tag.type == "enum":
            out[tag.key] = rng.choice(values)
        elif tag.type == "multi_enum":
            out[tag.key] = sorted(rng.sample(values, rng.randint(1, min(2, len(values)))), key=values.index)
    return out


async def create_fake_listings(session: AsyncSession, count: int, seed: int = 42) -> int:
    rng = random.Random(seed)
    categories = (
        await session.scalars(
            select(Category).where(
                Category.parent_id.is_not(None),
                Category.section_id == select(Section.id).where(Section.key == "empleo").scalar_subquery(),
                Category.is_enabled,
            )
        )
    ).all()
    specs: dict[int, list[AttributeDefinition]] = {}
    section_tags: list[AttributeDefinition] = []
    for a in (await session.scalars(select(AttributeDefinition))).all():
        if a.section_id is not None:
            section_tags.append(a)
        else:
            specs.setdefault(a.category_id, []).append(a)  # type: ignore[arg-type]

    geom = func.ST_GeomFromWKB(func.ST_AsBinary(Location.geog))
    places = (
        await session.execute(
            select(Location.id, Location.slug, Location.population, func.ST_X(geom), func.ST_Y(geom))
            .where(Location.level == "municipio")
            .order_by(Location.population.desc().nulls_last())
            .limit(400)
        )
    ).all()
    weights = [max(p[2] or 1, 1) ** 0.5 for p in places]  # big cities get more, but not all
    admin_id = await session.scalar(text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"))
    now = datetime.now(UTC)

    await session.execute(text("ALTER TABLE listings DISABLE TRIGGER listings_search_rebuild"))
    await session.execute(
        text("ALTER TABLE listing_translations DISABLE TRIGGER listing_translations_search_rebuild")
    )
    try:
        created = 0
        while created < count:
            size = min(BATCH, count - created)
            rows, texts = [], []
            for _ in range(size):
                category = rng.choice(categories)
                spain_wide = rng.random() < 0.08
                place = None if spain_wide else rng.choices(places, weights)[0]
                period = rng.choices(["month", "hour", "day", None], [70, 15, 5, 10])[0]
                base = {"month": (1100, 3500), "hour": (9, 20), "day": (70, 140), None: (0, 0)}[period]
                salary_min = rng.randint(*base) if period else None
                attributes = {}
                for spec in specs.get(category.id, []) + specs.get(category.parent_id or 0, []):
                    values = [o["value"] for o in spec.options]
                    if spec.type == "bool" and rng.random() < 0.4:
                        attributes[spec.key] = True
                    elif spec.type == "enum" and rng.random() < 0.7:
                        attributes[spec.key] = rng.choice(values)
                    elif spec.type == "multi_enum" and rng.random() < 0.8:
                        attributes[spec.key] = sorted(rng.sample(values, rng.randint(1, 2)), key=values.index)
                attributes.update(fake_section_tags(rng, section_tags, category.section_id))
                published = now - timedelta(minutes=rng.randint(0, 60 * 24 * 45))
                rows.append(
                    {
                        "section_id": category.section_id,
                        "category_id": category.id,
                        "location_id": place[0] if place else None,
                        "location_scope": "spain_wide" if spain_wide else "local",
                        "geog": None if spain_wide else f"SRID=4326;POINT({place[3]} {place[4]})",
                        "status": "active",
                        "original_lang": "uk",
                        "salary_min": salary_min,
                        "salary_max": None,
                        "salary_period": period,
                        "salary_monthly_min": monthly_min(salary_min, None, period),
                        "housing": rng.random() < 0.35,
                        "no_language": rng.random() < 0.3,
                        "no_experience": rng.random() < 0.25,
                        "schedule": rng.sample(["full", "part", "weekends", "shifts"], rng.randint(1, 2)),
                        "contract": rng.choice(["indefinido", "temporal", "fijo_discontinuo", None]),
                        "vacancies": rng.choice([None, None, 1, 2, 3, 5, 10]),
                        "is_urgent": rng.random() < 0.1,
                        "attributes": attributes,
                        "contact": MARKER,
                        "source": "partner",
                        "employer_name": rng.choice(COMPANIES),
                        "is_pinned": rng.random() < 0.01,
                        "published_at": published,
                        "expires_at": published + timedelta(days=60),
                        "created_by": admin_id,
                    }
                )
                texts.append((category, place))

            ids = (await session.execute(insert(Listing).returning(Listing.id), rows)).scalars().all()
            translations = []
            for listing_id, (category, place) in zip(ids, texts, strict=True):
                for lang in ("uk", "es"):
                    title = f"{category.name[lang]} {rng.choice(ADJECTIVES[lang])}"
                    translations.append(
                        {
                            "listing_id": listing_id,
                            "lang": lang,
                            "title": title,
                            "description": BODY[lang],
                            "slug": f"{slugify(title, lang)}-{place[1] if place else 'all-spain'}"[
                                :150
                            ].strip("-"),
                        }
                    )
            await session.execute(insert(ListingTranslation), translations)
            await session.commit()
            created += size
    finally:
        await session.execute(text("ALTER TABLE listings ENABLE TRIGGER listings_search_rebuild"))
        await session.execute(
            text("ALTER TABLE listing_translations ENABLE TRIGGER listing_translations_search_rebuild")
        )
        await session.commit()

    await session.execute(
        text("SELECT public.rebuild_listing_search(id) FROM listings WHERE contact @> CAST(:m AS jsonb)"),
        {"m": '{"_loadtest": true}'},
    )
    for table in ("listings", "listing_search", "listing_translations"):
        await session.execute(text(f"ANALYZE {table}"))
    await session.commit()
    return created


async def delete_fake_listings(session: AsyncSession) -> int:
    result = await session.execute(delete(Listing).where(is_fake()))
    await session.commit()
    return result.rowcount or 0
