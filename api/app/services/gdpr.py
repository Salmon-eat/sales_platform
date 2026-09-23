"""GDPR (admin spec §9): a person's data on request, erasure on request, anonymisation after the
retention period. Applications never disappear: contact data is wiped, statistics stay (sector, city,
language, source, status, dates)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Application, ApplicationFile, ApplicationMessage, ApplicationNote

ERASED_NAME = "—"
FINAL_STATUSES = ("done", "rejected")


async def person_applications(session: AsyncSession, application: Application) -> list[Application]:
    """A person is their normalised phone (admin spec §5); without a phone, just this application.

    Only the site's applications: the Telegram bot's are a mirror of the bot's own records, which follow the
    bot's rules, so the site never erases or exports them."""
    if application.source == "bot":
        return []
    if not application.phone:
        return [application]
    rows = await session.scalars(
        select(Application)
        .where(Application.phone == application.phone, Application.source != "bot")
        .order_by(Application.created_at)
    )
    return list(rows.all())


async def export_person(session: AsyncSession, application: Application) -> dict[str, Any]:
    """Everything we hold about the person (right of access / portability)."""
    items = []
    for a in await person_applications(session, application):
        messages = await session.scalars(
            select(ApplicationMessage)
            .where(ApplicationMessage.application_id == a.id)
            .order_by(ApplicationMessage.created_at)
        )
        notes = await session.scalars(
            select(ApplicationNote)
            .where(ApplicationNote.application_id == a.id)
            .order_by(ApplicationNote.created_at)
        )
        files = await session.scalars(select(ApplicationFile).where(ApplicationFile.application_id == a.id))
        items.append(
            {
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "name": a.name,
                "phone": a.phone,
                "messenger": a.messenger,
                "language": a.lang,
                "source": a.source,
                "status": a.status,
                "listing_id": a.listing_id,
                "category_id": a.category_id,
                "location_id": a.location_id,
                "answers": a.answers,
                "utm": a.utm,
                "ip": a.ip,
                "consent": {"at": a.consent_at.isoformat(), "policy_version": a.consent_version},
                "messages": [
                    {"from": m.author, "text": m.text, "at": m.created_at.isoformat()} for m in messages
                ],
                "manager_notes": [{"text": n.text, "at": n.created_at.isoformat()} for n in notes],
                # the files themselves are handed over separately (download from the application card)
                "cv_files": [
                    {"name": f.filename, "size": f.size, "at": f.created_at.isoformat()} for f in files
                ],
            }
        )
    return {"exported_at": datetime.now(UTC).isoformat(), "applications": items}


async def anonymize(session: AsyncSession, applications: list[Application]) -> int:
    """Wipe contact data and free text; keep what statistics need."""
    now = datetime.now(UTC)
    ids = [a.id for a in applications]
    for a in applications:
        a.name = ERASED_NAME
        a.phone = None
        a.ip = None
        a.utm = {}
        a.answers = {"in_spain": a.answers.get("in_spain")} if a.answers else {}
        a.chat_token = None  # the visitor's window starts afresh
        a.anonymized_at = now
    if ids:
        # conversations and manager notes are free text about the person
        await session.execute(delete(ApplicationMessage).where(ApplicationMessage.application_id.in_(ids)))
        await session.execute(delete(ApplicationNote).where(ApplicationNote.application_id.in_(ids)))
        await session.execute(delete(ApplicationFile).where(ApplicationFile.application_id.in_(ids)))  # CVs
    await session.commit()
    return len(ids)


async def anonymize_expired(session: AsyncSession) -> int:
    """Worker job: closed applications older than the retention period (default 24 months)."""
    before = datetime.now(UTC) - timedelta(days=30 * settings.anonymize_after_months)
    rows = await session.scalars(
        select(Application).where(
            Application.status.in_(FINAL_STATUSES),
            Application.source != "bot",  # the bot keeps its own records by its own rules
            Application.updated_at < before,
            Application.anonymized_at.is_(None),
        )
    )
    return await anonymize(session, list(rows.all()))
