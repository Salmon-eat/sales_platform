"""A site with people on it: firms, CVs, reviews, conversations, orders and a few articles.

Everything here hangs off a handful of accounts at `@demo.citobazar.invalid` — a domain that can never
receive mail — so `delete-demo-extras` finds and removes the lot without guessing.

Data goes in through the same services the website uses, so what you see locally is what a real visitor
would have produced.
"""

import io
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Category,
    Company,
    Conversation,
    Listing,
    ListingReport,
    Location,
    Order,
    Post,
    Resume,
    SavedSearch,
    Section,
    SellerReview,
    User,
)
from app.schemas.my import MyListingIn
from app.services import chats, my_listings, payments, photos, resumes, reviews
from app.services.accounts import get_or_create

DOMAIN = "demo.citobazar.invalid"

PEOPLE = {
    "oleg": ("Олег", "+34600111001"),
    "iryna": ("Ірина", "+34600111002"),
    "bohdan": ("Богдан", "+34600111003"),
    "remont": ("Ремонт під ключ", "+34600111004"),
    "limpieza": ("Clean Casa", "+34600111005"),
    "gestor": ("Gestoría Duero", "+34600111006"),
}

# (category slug, section key, title, description, price, kind, attributes)
ADS = [
    (
        "electronica", "articulos",
        "Ноутбук Lenovo ThinkPad, 16 ГБ",
        "Робочий ноутбук, 16 ГБ памʼяті, SSD 512 ГБ. Тримає батарею близько пʼяти годин. "
        "Є сумка і зарядка, подряпин немає.",
        320, "negotiable", {"condition": "used", "delivery": ["pickup", "shipping"]},
    ),
    (
        "casa-y-jardin", "articulos",
        "Диван розкладний, тканина сіра",
        "Розкладається в повноцінне ліжко 140×200. Купували два роки тому, переїжджаємо. "
        "Самовивіз, допоможу винести.",
        180, "fixed", {"condition": "used", "delivery": ["pickup"]},
    ),
    (
        "motos", "motor",
        "Honda PCX 125, 2020, 14 000 км",
        "Скутер у доброму стані, обслуговування вчасне, гума торік нова. "
        "Підійде для роботи кур'єром або щоденних поїздок.",
        2100, "negotiable", {"fuel": "gasolina", "vehicle_age": "3to10"},
    ),
]

COMPANIES = [
    (
        "remont", "Ремонт під ключ Мадрид", "uk",
        "Бригада з десятирічним досвідом: плитка, сантехніка, електрика, фарбування.\n"
        "Робимо ванні кімнати й кухні під ключ, кошторис безкоштовно, працюємо з рахунком.",
        "madrid", "Calle Bravo Murillo 120", "Пн–Пт 9:00–18:00, Сб до 14:00",
        ("reformas", "mudanzas"), "+34600111004", "@remontmadrid", "remont-madrid.example.com",
        True, True,   # verified, promoted
    ),
    (
        "limpieza", "Clean Casa", "es",
        "Limpieza de pisos, oficinas y finales de obra. Productos incluidos, equipo propio.\n"
        "Trabajamos en Valencia capital y alrededores, con factura.",
        "valencia", "Carrer de Colón 24", "L–S 8:00–20:00",
        ("limpieza",), "+34600111005", None, None,
        True, False,
    ),
    (
        "gestor", "Gestoría Duero", "es",
        "NIE, empadronamiento, alta de autónomo, declaraciones y canje del permiso de conducir.\n"
        "Atendemos en español, ucraniano y ruso.",
        "barcelona", "Gran Via 455", "L–V 9:00–17:00",
        ("juridico", "traducciones"), "+34600111006", "@gestoriaduero", None,
        False, False,
    ),
]

RESUMES = [
    (
        "bohdan",
        {
            "title": "Водій категорії CE",
            "about": "Вісім років на міжнародних рейсах: тент, рефрижератор. Працював по Іспанії, "
            "Франції та Німеччині. Права CE, код 95 і ADR чинні.",
            "experience_years": 8,
            "licences": ["b", "c", "ce", "code95", "adr"],
            "languages": {"uk": "native", "ru": "c1", "es": "a2"},
            "schedule": ["full"],
            "salary_min": 2200,
            "salary_period": "month",
            "work_permit": True,
            "has_car": True,
            "relocate": True,
        },
    ),
    (
        "iryna",
        {
            "title": "Прибиральниця, досвід у готелях",
            "about": "Три роки в готелях Валенсії, знаю роботу покоївки й прибирання після ремонту. "
            "Акуратна, можу виходити у вихідні.",
            "experience_years": 3,
            "licences": ["b"],
            "languages": {"uk": "native", "es": "b1", "en": "a2"},
            "schedule": ["full", "weekends"],
            "salary_min": 1400,
            "salary_period": "month",
            "work_permit": True,
        },
    ),
]

POSTS = [
    (
        "uk",
        "Як обміняти водійське посвідчення в Іспанії",
        "Що зібрати, скільки це триває і коли обмін узагалі не потрібен.",
        "Обмін прав залежить від того, яка країна їх видала, і від того, скільки ви вже в Іспанії.\n\n"
        "Перші шість місяців українським посвідченням можна користуватися як є. Після цього потрібен "
        "обмін: переклад посвідчення, медична довідка з центру psicotécnico, прописка і запис у Trafico.\n\n"
        "Запис у великих містах іде на кілька тижнів наперед, тож починати варто одразу після прописки. "
        "Саму справу розглядають зазвичай місяць-півтора, і весь цей час можна їздити за довідкою.\n\n"
        "Категорії C і CE обмінюються складніше: до пакета додається медогляд для професійних водіїв, "
        "а код 95 доведеться підтверджувати окремо курсом.",
    ),
    (
        "uk",
        "Скільки коштує зняти житло в Іспанії: чого чекати крім оренди",
        "Застава, комісія агенції, комуналка — з чого складається перший платіж.",
        "Оголошення показує ціну за місяць, але перший платіж завжди більший.\n\n"
        "Стандартно просять заставу за один-два місяці (fianza) і, якщо квартиру здає агенція, "
        "її комісію — ще один місяць. Разом перший раз віддаєте три-чотири місячні платежі.\n\n"
        "Комуналка (gastos) буває включена або ні — це завжди написано в оголошенні. Якщо ні, "
        "рахуйте ще 80–150 € на місяць за воду, світло й інтернет, залежно від розміру квартири.\n\n"
        "Власники часто просять довідку з роботи (nómina) і контракт. Без них шукати складніше, "
        "але реально: допомагає більша застава або поручитель.",
    ),
    (
        "es",
        "Cómo publicar un anuncio que responden",
        "Fotos, precio y primeras líneas: lo que decide si te escriben.",
        "Un anuncio con foto recibe varias veces más respuestas que uno sin ella. No hace falta una "
        "cámara: basta luz de día y un fondo limpio.\n\n"
        "Pon el precio aunque sea negociable. Los anuncios sin precio se abren menos, porque la gente "
        "no sabe si merece la pena preguntar.\n\n"
        "Las dos primeras líneas se ven en la lista. Escribe ahí lo más importante: qué es, en qué "
        "estado está y dónde se puede recoger.\n\n"
        "Y contesta rápido: la mayoría de los compradores escriben a tres o cuatro vendedores a la vez.",
    ),
    (
        "es",
        "Trabajar en España sin hablar español: qué es posible",
        "Sectores donde el idioma no cierra la puerta, y qué palabras conviene aprender igualmente.",
        "Hay trabajos donde el idioma casi no hace falta al principio: almacén, obra, limpieza, "
        "recolección agrícola, reparto con aplicación.\n\n"
        "En hostelería ya cambia: en cocina se puede empezar sin idioma, en sala no.\n\n"
        "Aun así, merece la pena aprender treinta o cuarenta palabras del oficio. Con eso se entiende "
        "una orden, se pide una herramienta y se evita la mitad de los malentendidos.\n\n"
        "Para conducir camiones el idioma sí importa: hay que entender al cliente y a la Guardia Civil.",
    ),
]


def _picture(width: int, height: int, colour: tuple[int, int, int]) -> bytes:
    """A plain coloured picture: enough to see the layout without shipping photos in the repo."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, "PNG")
    return buffer.getvalue()


async def _person(session: AsyncSession, key: str) -> User:
    name, phone = PEOPLE[key]
    user = await get_or_create(session, email=f"demo.{key}@{DOMAIN}", name=name, lang="uk")
    user.phone = phone
    await session.commit()
    return user


async def _publish(session: AsyncSession, listing: Listing, days_ago: int = 0) -> None:
    now = datetime.now(UTC)
    listing.status = "active"
    listing.published_at = now - timedelta(days=days_ago, hours=days_ago)
    listing.expires_at = now + timedelta(days=30)
    await session.commit()


async def seed_demo_extras(session: AsyncSession) -> dict[str, int]:
    """Everything a person would see on a site that is already being used."""
    if await session.scalar(select(User.id).where(User.email.like(f"%@{DOMAIN}")).limit(1)):
        return {}

    people = {key: await _person(session, key) for key in PEOPLE}
    made = {"people": len(people)}

    # ---- ads from a private seller, one of them paid for
    ads: list[Listing] = []
    for index, (category_slug, section_key, title, description, price, kind, attributes) in enumerate(ADS):
        category_id = await session.scalar(
            select(Category.id)
            .join(Section, Section.id == Category.section_id)
            .where(
                Section.key == section_key,
                Category.slug["es"].astext == category_slug,
                Category.is_enabled.is_(True),
            )
        )
        town_id = await session.scalar(
            select(Location.id).where(Location.slug == "valencia", Location.level == "municipio")
        )
        listing = await my_listings.save(
            session,
            people["oleg"],
            MyListingIn(
                category_id=category_id,
                location_id=town_id,
                lang="uk",
                title=title,
                description=description,
                price=price,
                price_kind=kind,
                attributes=attributes,
                contact={"name": "Олег", "phone": PEOPLE["oleg"][1]},
            ),
        )
        await my_listings.add_photo(
            session, people["oleg"], listing, _picture(1200, 900, (190 - index * 30, 150, 110 + index * 40))
        )
        await _publish(session, listing, days_ago=index)
        ads.append(listing)
    made["ads"] = len(ads)

    # one ad is highlighted and one is in the top block, through a real paid order
    for product, listing in (("highlight_7", ads[0]), ("top_7", ads[1])):
        order = await payments.create(session, people["oleg"], product, listing.id)
        await payments.mark_paid(session, order, "manual", "demo")
    # and one order still waiting, so the admin has something to confirm
    await payments.create(session, people["oleg"], "bump", ads[2].id)
    made["orders"] = 3

    # ---- somebody writes about an ad, then leaves a review
    chat = await chats.start(session, people["iryna"], ads[0].id, "Доброго дня! Ноутбук ще актуальний?")
    await chats.add_message(session, chat, people["oleg"], "Так, актуальний. Можу показати сьогодні ввечері.")
    await chats.add_message(session, chat, people["iryna"], "Чудово, напишу ближче до шостої.")
    await reviews.leave(
        session,
        people["iryna"],
        people["oleg"].id,
        5,
        "Усе як в описі, зустрілися вчасно. Ноутбук справді в доброму стані.",
        ads[0].id,
    )
    mine = await session.scalar(
        select(SellerReview).where(SellerReview.seller_id == people["oleg"].id)
    )
    await reviews.answer(session, people["oleg"], mine.id, "Дякую за покупку!")
    made["reviews"] = 1

    # ---- a saved search, so the cabinet is not empty
    session.add(
        SavedSearch(
            user_id=people["iryna"].id,
            title="Речі у Валенсії",
            lang="uk",
            section_key="articulos",
            params={"sort": "new"},
            last_seen_id=max(ad.id for ad in ads),
        )
    )
    await session.commit()
    made["searches"] = 1

    # ---- CVs
    for key, data in RESUMES:
        town_id = await session.scalar(
            select(Location.id).where(Location.slug == "valencia", Location.level == "municipio")
        )
        from app.schemas.resume import ResumeIn

        await resumes.save(session, people[key], ResumeIn(city_id=town_id, **data))
    made["resumes"] = len(RESUMES)

    # ---- firms
    from app.schemas.company import CompanyIn
    from app.services import companies as company_service

    firms = 0
    for (
        key, name, lang, about, town_slug, address, hours, category_slugs, phone, telegram, site,
        verified, promoted,
    ) in COMPANIES:
        town_id = await session.scalar(
            select(Location.id).where(Location.slug == town_slug, Location.level == "municipio")
        )
        # the trades live in the services section; the same slugs exist in jobs and mean something else
        category_ids = list(
            (
                await session.scalars(
                    select(Category.id)
                    .join(Section, Section.id == Category.section_id)
                    .where(
                        Section.key == "servicios-sec",
                        Category.slug["es"].astext.in_(category_slugs),
                        Category.is_enabled.is_(True),
                    )
                )
            ).all()
        )
        firm = await company_service.save(
            session,
            people[key],
            CompanyIn(
                name=name,
                lang=lang,
                about=about,
                city_id=town_id,
                address=address,
                hours=hours,
                category_ids=category_ids,
                phone=phone,
                telegram=telegram,
                site=site,
            ),
        )
        firm.logo = photos.save(_picture(400, 400, (255, 106, 26) if verified else (60, 90, 150)))[0]
        if verified:
            await company_service.approve(session, firm.id, people["oleg"], verified=True)
        else:
            # left waiting, so the moderation queue has something in it
            firm.status = "pending"
        if promoted:
            firm.promoted_until = datetime.now(UTC) + timedelta(days=30)
        await session.commit()
        firms += 1
    made["companies"] = firms

    # ---- articles
    for lang, title, excerpt, body in POSTS:
        from app.core.slug import slugify

        session.add(
            Post(
                slug=slugify(title, lang)[:150],
                lang=lang,
                title=title,
                excerpt=excerpt,
                body=body,
                status="published",
                author_id=people["oleg"].id,
                published_at=datetime.now(UTC) - timedelta(days=len(made)),
            )
        )
    await session.commit()
    made["posts"] = len(POSTS)

    # ---- one ad waiting to be checked and one complaint, so the admin queues are not empty
    category_id = await session.scalar(
        select(Category.id)
        .join(Section, Section.id == Category.section_id)
        .where(Section.key == "articulos", Category.slug["es"].astext == "moda")
    )
    town_id = await session.scalar(
        select(Location.id).where(Location.slug == "madrid", Location.level == "municipio")
    )
    waiting = await my_listings.save(
        session,
        people["iryna"],
        MyListingIn(
            category_id=category_id,
            location_id=town_id,
            lang="uk",
            title="Куртка зимова, розмір М",
            description="Тепла куртка, носили один сезон. Колір темно-синій, капюшон знімається.",
            price=45,
            price_kind="fixed",
            attributes={"condition": "like_new", "delivery": ["pickup"]},
            contact={"name": "Ірина", "phone": PEOPLE["iryna"][1]},
        ),
    )
    await my_listings.submit(session, people["iryna"], waiting)
    made["pending"] = 1

    session.add(
        ListingReport(
            listing_id=ads[2].id,
            reporter_id=people["bohdan"].id,
            reason="sold",
            note="Писав продавцю — каже, що вже продав.",
        )
    )
    await session.commit()
    made["reports"] = 1
    return made


async def delete_demo_extras(session: AsyncSession) -> dict[str, int]:
    """Everything hangs off the demo accounts, so removing them removes the lot."""
    people = (await session.scalars(select(User).where(User.email.like(f"%@{DOMAIN}")))).all()
    if not people:
        return {}
    ids = [person.id for person in people]

    removed = {"posts": 0, "listings": 0, "companies": 0, "orders": 0, "people": len(ids)}

    for post in (await session.scalars(select(Post).where(Post.author_id.in_(ids)))).all():
        await session.delete(post)
        removed["posts"] += 1

    for firm in (await session.scalars(select(Company).where(Company.owner_id.in_(ids)))).all():
        if firm.logo:
            photos.delete(firm.logo)
        await session.delete(firm)
        removed["companies"] += 1

    for listing in (await session.scalars(select(Listing).where(Listing.owner_id.in_(ids)))).all():
        await session.refresh(listing, ["photos"])
        for photo in listing.photos:
            photos.delete(photo.path)
        await session.delete(listing)
        removed["listings"] += 1

    for order in (await session.scalars(select(Order).where(Order.user_id.in_(ids)))).all():
        await session.delete(order)
        removed["orders"] += 1

    # conversations, reviews, resumes and saved searches go with their owners
    for table in (Conversation, SellerReview, Resume, SavedSearch, ListingReport):
        column = {
            Conversation: Conversation.buyer_id,
            SellerReview: SellerReview.author_id,
            Resume: Resume.user_id,
            SavedSearch: SavedSearch.user_id,
            ListingReport: ListingReport.reporter_id,
        }[table]
        for row in (await session.scalars(select(table).where(column.in_(ids)))).all():
            await session.delete(row)

    for person in people:
        await session.delete(person)
    await session.commit()
    return removed
