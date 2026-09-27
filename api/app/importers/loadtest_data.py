"""Test ads at real scale (spec §11: 10k listings, p95 of list+facets < 300 ms).

A business does not start with a thousand ads either — which is exactly why the site has to be tried
at that size before anyone depends on it. This fills every section, not only jobs: flats with a monthly
rent, cars with a price, things people sell, services, courses, pets. Ads carry pictures, so the cards,
the galleries and the page weight are tested too.

Every row carries contact = {"_loadtest": true} (never shown on the site) and every picture lives in
one folder, so delete-fake-listings takes all of it away again.

Titles are composed from the category names, which we already keep in four languages, plus a short
modifier from a list per language. Nothing here is machine-translated: it is assembled from our own
dictionaries, the same rule the real site follows.

Triggers are disabled during the bulk insert and the search documents are rebuilt once at the end.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slug import slugify
from app.importers.placeholder_images import build_pool, delete_pool
from app.models import (
    AttributeDefinition,
    Category,
    Listing,
    ListingPhoto,
    ListingTranslation,
    Location,
    Section,
)
from app.services.listing_rules import monthly_min

MARKER = {"_loadtest": True}  # in listings.contact
BATCH = 500
LANGS = ("es", "uk", "ru", "en")

COMPANIES = [
    "Transportes Levante", "Logística Ibérica", "Hostelería Mediterránea", "Grupo Costa Sol",
    "Agrícola del Sur", "Construcciones Norte", "Limpiezas Brillo", "Almacenes Centro",
    "Cuidados en Casa", "Frutas Huerta Viva",
]  # fmt: skip


def is_fake():  # noqa: ANN201
    return Listing.contact.contains(MARKER)


# ---------------------------------------------------------------- what each section looks like

# how the ads are spread; anything not named here gets the leftover weight
SECTION_WEIGHTS = {
    "empleo": 32,
    "articulos": 22,
    "inmobiliaria": 15,
    "motor": 14,
    "servicios-sec": 7,
    "animales": 3,
    "negocios": 3,
    "formacion-sec": 2,
    "comunidad": 2,
}
OTHER_WEIGHT = 2

# (lowest, highest, share paid per month rather than once, share with no price at all)
PRICES = {
    "inmobiliaria": (320, 2400, 0.75, 0.02),
    "motor": (600, 24000, 0.0, 0.05),
    "articulos": (5, 900, 0.0, 0.12),
    "animales": (0, 500, 0.0, 0.45),
    "negocios": (400, 45000, 0.15, 0.10),
    "servicios-sec": (15, 1500, 0.0, 0.25),
    "formacion-sec": (20, 600, 0.35, 0.15),
    "comunidad": (0, 60, 0.0, 0.80),
}

# short additions that make two ads in the same category look like two ads, and give the search
# something to match beyond the category name
MODIFIERS = {
    "goods": {
        "es": ["como nuevo", "poco uso", "con garantía", "buen estado", "se negocia", "recogida en mano"],
        "uk": ["як новий", "мало користувалися", "з гарантією", "гарний стан", "торг", "самовивіз"],
        "ru": ["как новый", "мало пользовались", "с гарантией", "хорошее состояние", "торг", "самовывоз"],
        "en": ["as new", "barely used", "under warranty", "good condition", "price negotiable"],
    },
    "home": {
        "es": ["con muebles", "sin comisión", "cerca del metro", "exterior y luminoso", "reformado"],
        "uk": ["з меблями", "без комісії", "біля метро", "світла, на вулицю", "після ремонту"],
        "ru": ["с мебелью", "без комиссии", "рядом метро", "светлая, на улицу", "после ремонта"],
        "en": ["furnished", "no agency fee", "near the metro", "bright and outward-facing", "renovated"],
    },
    "jobs": {
        "es": ["urgente", "con experiencia", "sin experiencia", "temporada", "fin de semana", "turno de noche"],
        "uk": ["терміново", "з досвідом", "без досвіду", "сезон", "вихідні", "нічна зміна"],
        "ru": ["срочно", "с опытом", "без опыта", "сезон", "выходные", "ночная смена"],
        "en": ["urgent", "experience required", "no experience needed", "seasonal", "weekends", "night shift"],
    },
    "services": {
        "es": ["presupuesto sin compromiso", "a domicilio", "10 años de experiencia", "fines de semana"],
        "uk": ["безкоштовний кошторис", "з виїздом", "досвід 10 років", "працюємо у вихідні"],
        "ru": ["бесплатная смета", "с выездом", "опыт 10 лет", "работаем в выходные"],
        "en": ["free quote", "we come to you", "ten years of experience", "weekends too"],
    },
}
KIND_OF_SECTION = {
    "empleo": "jobs",
    "inmobiliaria": "home",
    "servicios-sec": "services",
    "formacion-sec": "services",
    "comunidad": "goods",
}

BODIES = {
    "goods": {
        "es": "En buen estado y listo para llevar. Se puede ver antes de comprar; entrega en mano en la ciudad.",
        "uk": "У доброму стані, готове до передачі. Можна оглянути перед покупкою, зустріч у місті.",
        "ru": "В хорошем состоянии, готово к передаче. Можно посмотреть перед покупкой, встреча в городе.",
        "en": "In good condition and ready to go. You can see it before buying; handover in the city.",
    },
    "home": {
        "es": "Vivienda lista para entrar. Gastos aparte salvo indicación; se piden nómina y fianza habitual.",
        "uk": "Житло готове до заселення. Комунальні окремо, якщо не вказано інше; потрібні довідка про дохід і застава.",
        "ru": "Жильё готово к заселению. Коммунальные отдельно, если не указано иное; нужны справка о доходе и залог.",
        "en": "Ready to move into. Bills separate unless stated; proof of income and the usual deposit required.",
    },
    "jobs": {
        "es": "Buscamos personal para incorporación inmediata. Contrato, alta en la Seguridad Social y buen ambiente.",
        "uk": "Шукаємо працівників із виходом одразу. Офіційне оформлення, стабільні виплати й житло за потреби.",
        "ru": "Ищем работников с выходом сразу. Официальное оформление, стабильные выплаты и жильё при необходимости.",
        "en": "We are hiring with an immediate start. Proper contract, social security and a decent team.",
    },
    "services": {
        "es": "Trabajo garantizado y presupuesto cerrado antes de empezar. Atendemos en toda la provincia.",
        "uk": "Гарантія на роботу і кошторис до початку. Працюємо по всій провінції.",
        "ru": "Гарантия на работу и смета до начала. Работаем по всей провинции.",
        "en": "Guaranteed work and a fixed quote before we start. We cover the whole province.",
    },
}

# a real board is not written in every language at once: Spanish always, the rest as it comes
LANG_SHARE = {"es": 1.0, "uk": 0.7, "ru": 0.45, "en": 0.25}
# how often an ad has pictures, by section kind
PHOTO_SHARE = {"jobs": 0.15, "home": 0.9, "services": 0.4, "goods": 0.85}


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


def fake_vehicle(rng: random.Random, category_slug: str, attrs: dict[str, object]) -> dict[str, object]:
    """Year, kilometres and the DGT label that belong together, the way a real car's do: a 2008 diesel
    has done 200 000 km and gets no label; a 2022 hybrid has 40 000 and the ECO sticker."""
    if category_slug == "recambios":  # spare parts have no year or mileage
        return {}
    year = min(2026, max(1998, round(rng.triangular(2002, 2026, 2019))))
    age = max(2026 - year, 0)
    per_year = {"motos": (2_000, 7_000), "camiones": (40_000, 90_000), "remolques": (0, 0)}.get(
        category_slug, (9_000, 19_000)
    )
    # a lorry rarely comes to sale past ~1.2 million km, a car past ~400 000
    ceiling = {"camiones": 1_200_000, "motos": 120_000}.get(category_slug, 400_000)
    out: dict[str, object] = {"year": year}
    if per_year[1]:
        out["km"] = min(round(age * rng.randint(*per_year) + rng.randint(0, 9_000), -2), ceiling)
    fuel = attrs.get("fuel")
    if fuel == "electrico":
        out["dgt_label"] = "cero"
    elif fuel in {"hibrido", "gas"}:
        out["dgt_label"] = "eco"
    elif fuel == "diesel":
        out["dgt_label"] = "c" if year >= 2015 else "b" if year >= 2006 else "sin"
    elif fuel == "gasolina":
        out["dgt_label"] = "c" if year >= 2006 else "b" if year >= 2001 else "sin"
    return out


def _money(rng: random.Random, section_key: str) -> dict[str, object]:
    """What the card shows first: a salary in jobs, a price everywhere else."""
    if section_key == "empleo":
        period = rng.choices(["month", "hour", "day", None], [70, 15, 5, 10])[0]
        span = {"month": (1100, 3500), "hour": (9, 20), "day": (70, 140), None: (0, 0)}[period]
        salary = rng.randint(*span) if period else None
        return {
            "salary_min": salary,
            "salary_period": period,
            "salary_monthly_min": monthly_min(salary, None, period),
        }
    low, high, monthly, free = PRICES.get(section_key, (10, 500, 0.0, 0.2))
    if rng.random() < free:
        return {"price": None, "price_kind": "free" if rng.random() < 0.5 else "negotiable"}
    if rng.random() < monthly:
        return {"price": rng.randint(low, min(high, 2500)), "price_period": "month", "price_kind": "fixed"}
    amount = rng.randint(low, high) if section_key != "inmobiliaria" else rng.randint(45_000, 390_000)
    return {"price": amount, "price_kind": rng.choices(["fixed", "negotiable", "from"], [75, 20, 5])[0]}


def _title(
    rng: random.Random, category: Category, section_key: str, lang: str, place_name: str | None
) -> str:
    name = category.name.get(lang) or category.name["es"]
    kind = KIND_OF_SECTION.get(section_key, "goods")
    words = MODIFIERS[kind].get(lang) or MODIFIERS[kind]["es"]
    title = f"{name} — {rng.choice(words)}"
    if place_name and rng.random() < 0.4:
        title = f"{title}, {place_name}"
    return title[:200]


# ---------------------------------------------------------------- the generator


async def create_fake_listings(
    session: AsyncSession, count: int, seed: int = 42, with_photos: bool = True
) -> int:
    rng = random.Random(seed)

    sections = {
        s.id: s
        for s in (
            await session.scalars(
                select(Section).where(Section.is_enabled, Section.kind == "listings")
            )
        ).all()
    }
    if not sections:
        return 0

    # Jobs go two levels deep (sector -> profession) and the ad belongs to the profession. Goods, motor
    # and the rest are one level, so there the top level is where the ad belongs. Both lists are
    # collected first and the choice is made per section — picking as we go would have filled a whole
    # section from its first category alone.
    children: dict[int, list[Category]] = {}
    tops: dict[int, list[Category]] = {}
    for c in (await session.scalars(select(Category).where(Category.is_enabled))).all():
        if c.section_id not in sections:
            continue
        (children if c.parent_id is not None else tops).setdefault(c.section_id, []).append(c)
    categories_by_section = {
        sid: children.get(sid) or tops.get(sid, []) for sid in sections
    }

    usable = [sid for sid in sections if categories_by_section.get(sid)]
    weights = [SECTION_WEIGHTS.get(sections[sid].key, OTHER_WEIGHT) for sid in usable]

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
            select(
                Location.id, Location.slug, Location.population, func.ST_X(geom), func.ST_Y(geom),
                Location.names,
            )
            .where(Location.level == "municipio")
            .order_by(Location.population.desc().nulls_last())
            .limit(400)
        )
    ).all()
    place_weights = [max(p[2] or 1, 1) ** 0.5 for p in places]  # big cities get more, but not all
    admin_id = await session.scalar(text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"))
    now = datetime.now(UTC)

    pool = build_pool() if with_photos else []

    await session.execute(text("ALTER TABLE listings DISABLE TRIGGER listings_search_rebuild"))
    await session.execute(
        text("ALTER TABLE listing_translations DISABLE TRIGGER listing_translations_search_rebuild")
    )
    try:
        created = 0
        while created < count:
            size = min(BATCH, count - created)
            rows: list[dict[str, object]] = []
            context: list[tuple[Category, object, str]] = []
            for _ in range(size):
                section = sections[rng.choices(usable, weights)[0]]
                category = rng.choice(categories_by_section[section.id])
                spain_wide = section.key == "empleo" and rng.random() < 0.08
                place = None if spain_wide else rng.choices(places, place_weights)[0]

                attributes: dict[str, object] = {}
                for spec in specs.get(category.id, []) + specs.get(category.parent_id or 0, []):
                    values = [o["value"] for o in spec.options]
                    if spec.type == "bool" and rng.random() < 0.4:
                        attributes[spec.key] = True
                    elif spec.type == "enum" and rng.random() < 0.7:
                        attributes[spec.key] = rng.choice(values)
                    elif spec.type == "multi_enum" and rng.random() < 0.8:
                        attributes[spec.key] = sorted(rng.sample(values, rng.randint(1, 2)), key=values.index)
                attributes.update(fake_section_tags(rng, section_tags, section.id))
                if section.key == "motor":
                    attributes.update(fake_vehicle(rng, category.slug["es"], attributes))

                jobs = section.key == "empleo"
                published = now - timedelta(minutes=rng.randint(0, 60 * 24 * 45))
                row: dict[str, object] = {
                    "section_id": section.id,
                    "category_id": category.id,
                    "location_id": place[0] if place else None,
                    "location_scope": "spain_wide" if spain_wide else "local",
                    "geog": None if spain_wide else f"SRID=4326;POINT({place[3]} {place[4]})",
                    "status": "active",
                    "original_lang": rng.choices(["uk", "es", "ru"], [50, 40, 10])[0],
                    "housing": jobs and rng.random() < 0.35,
                    "no_language": jobs and rng.random() < 0.3,
                    "no_experience": jobs and rng.random() < 0.25,
                    "schedule": rng.sample(["full", "part", "weekends", "shifts"], rng.randint(1, 2))
                    if jobs
                    else [],
                    "contract": rng.choice(["indefinido", "temporal", "fijo_discontinuo", None])
                    if jobs
                    else None,
                    "vacancies": rng.choice([None, None, 1, 2, 3, 5, 10]) if jobs else None,
                    "is_urgent": rng.random() < 0.1,
                    "attributes": attributes,
                    "contact": MARKER,
                    "source": "partner",
                    "employer_name": rng.choice(COMPANIES) if jobs else None,
                    "is_pinned": rng.random() < 0.01,
                    "published_at": published,
                    "expires_at": published + timedelta(days=60),
                    "created_by": admin_id,
                }
                row.update(_money(rng, section.key))
                rows.append(row)
                context.append((category, place, section.key))

            ids = (await session.execute(insert(Listing).returning(Listing.id), rows)).scalars().all()

            translations: list[dict[str, object]] = []
            photos: list[dict[str, object]] = []
            for listing_id, (category, place, section_key) in zip(ids, context, strict=True):
                place_names = place[5] if place else None
                for lang in LANGS:
                    if lang != "es" and rng.random() > LANG_SHARE[lang]:
                        continue
                    local_place = (place_names or {}).get(lang) if place_names else None
                    title = _title(rng, category, section_key, lang, local_place)
                    kind = KIND_OF_SECTION.get(section_key, "goods")
                    slug = f"{slugify(title, lang)}-{place[1] if place else 'all-spain'}"[:150].strip("-")
                    translations.append(
                        {
                            "listing_id": listing_id,
                            "lang": lang,
                            "title": title,
                            "description": BODIES[kind][lang],
                            "slug": slug or f"anuncio-{listing_id}",
                        }
                    )
                if pool:
                    kind = KIND_OF_SECTION.get(section_key, "goods")
                    if rng.random() < PHOTO_SHARE[kind]:
                        for sort, (path, width, height, bytes_) in enumerate(
                            rng.sample(pool, rng.randint(1, 4))
                        ):
                            photos.append(
                                {
                                    "listing_id": listing_id,
                                    "path": path,
                                    "width": width,
                                    "height": height,
                                    "size": bytes_,
                                    "sort": sort,
                                }
                            )

            await session.execute(insert(ListingTranslation), translations)
            if photos:
                await session.execute(insert(ListingPhoto), photos)
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
    for table in ("listings", "listing_search", "listing_translations", "listing_photos"):
        await session.execute(text(f"ANALYZE {table}"))
    await session.commit()
    return created


async def delete_fake_listings(session: AsyncSession) -> int:
    result = await session.execute(delete(Listing).where(is_fake()))
    await session.commit()
    delete_pool()
    return result.rowcount or 0
