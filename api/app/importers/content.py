"""Static page texts from seeds/content.json (upsert by key + lang)."""

import asyncio
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pages import ContentBlock

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "content.json"


async def seed_content(session: AsyncSession, path: Path = SEED_FILE) -> int:
    data = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))
    rows = [
        {"key": key, "lang": lang, "title": v["title"], "body": v.get("body", ""), "data": v.get("data", {})}
        for key, langs in data["blocks"].items()
        for lang, v in langs.items()
    ]
    stmt = insert(ContentBlock)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_content_blocks_key_lang",
        set_={"title": stmt.excluded.title, "body": stmt.excluded.body, "data": stmt.excluded.data},
    )
    await session.execute(stmt, rows)
    await session.commit()
    return len(rows)
