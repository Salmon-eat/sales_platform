"""Idempotent taxonomy seed from seeds/taxonomy.json.

Identity: section.key, category (section, parent, slug.es), attribute (category, key).
Existing rows are updated in place, so ids stay stable and slug changes land in slug_history.
"""

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttributeDefinition, Category, Section
from app.models.i18n import LANGS
from app.models.taxonomy import SECTION_KINDS

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "taxonomy.json"
ATTRIBUTE_TYPES = {"bool", "enum", "multi_enum", "int_range"}


class SeedError(ValueError):
    pass


@dataclass
class SeedReport:
    sections: int = 0
    categories: int = 0
    attributes: int = 0
    warnings: list[str] = field(default_factory=list)


def _require_langs(value: dict[str, Any] | None, where: str) -> dict[str, Any]:
    missing = [lang for lang in LANGS if not (value or {}).get(lang)]
    if missing:
        raise SeedError(f"{where}: missing translations {missing}")
    return value  # type: ignore[return-value]


async def _upsert_attribute(
    session: AsyncSession,
    data: dict[str, Any],
    *,
    category: Category | None = None,
    section: Section | None = None,
) -> None:
    """An attribute of a category (tier 3) or a tag of a whole section (tier 2)."""
    owner = f"category {category.slug['es']}" if category else f"section {section.key}"  # type: ignore[union-attr]
    where = f"attribute {data.get('key')} of {owner}"
    if data.get("type") not in ATTRIBUTE_TYPES:
        raise SeedError(f"{where}: unknown type {data.get('type')!r}")
    options = data.get("options", [])
    if data["type"] in {"enum", "multi_enum"} and not options:
        raise SeedError(f"{where}: enum attributes need options")
    for option in options:
        _require_langs(option.get("label"), f"{where} option {option.get('value')}")

    owner_condition = (
        AttributeDefinition.category_id == category.id
        if category
        else AttributeDefinition.section_id == section.id  # type: ignore[union-attr]
    )
    attr = await session.scalar(
        select(AttributeDefinition).where(owner_condition, AttributeDefinition.key == data["key"])
    )
    if attr is None:
        attr = AttributeDefinition(
            category_id=category.id if category else None,
            section_id=section.id if section and not category else None,
            key=data["key"],
        )
        session.add(attr)
    attr.type = data["type"]
    attr.label = _require_langs(data.get("label"), where)
    attr.options = options
    attr.filterable = data.get("filterable", True)
    attr.facet_order = data.get("facet_order", 0)
    attr.required = data.get("required", False)
    attr.seo_indexable = data.get("seo_indexable", False)


async def _upsert_category(
    session: AsyncSession,
    report: SeedReport,
    section: Section,
    parent: Category | None,
    data: dict[str, Any],
    sort: int,
    section_keys: set[str],
) -> None:
    slug = _require_langs(data.get("slug"), f"category in {section.key}")
    where = f"category {slug['es']}"

    category = await session.scalar(
        select(Category).where(
            Category.section_id == section.id,
            Category.parent_id.is_(None) if parent is None else Category.parent_id == parent.id,
            Category.slug["es"].astext == slug["es"],
        )
    )
    if category is None:
        category = Category(section_id=section.id, parent_id=parent.id if parent else None)
        session.add(category)
    category.slug = slug
    category.name = _require_langs(data.get("name"), where)
    category.synonyms = data.get("synonyms", {})
    category.icon = data.get("icon")
    category.sort = data.get("sort", sort)
    category.is_enabled = data.get("is_enabled", True)
    category.seo_text = data.get("seo_text", {})
    await session.flush()
    report.categories += 1

    for attribute in data.get("attributes", []):
        if attribute.get("key") in section_keys:
            # both live in listings.attributes: one key, one meaning
            raise SeedError(f"{where}: attribute {attribute['key']!r} clashes with a tag of {section.key}")
        await _upsert_attribute(session, attribute, category=category)
        report.attributes += 1

    for i, child in enumerate(data.get("children", []), start=1):
        if parent is not None:
            raise SeedError(f"{where}: professions cannot have children (max depth is sector -> profession)")
        await _upsert_category(session, report, section, category, child, i, section_keys)


def load_seed(path: Path = SEED_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


async def seed_taxonomy(session: AsyncSession, path: Path = SEED_FILE) -> SeedReport:
    data = await asyncio.to_thread(load_seed, path)
    report = SeedReport()

    for i, item in enumerate(data["sections"], start=1):
        section = await session.scalar(select(Section).where(Section.key == item["key"]))
        if section is None:
            section = Section(key=item["key"])
            session.add(section)
        section.slug = _require_langs(item.get("slug"), f"section {item['key']}")
        section.name = _require_langs(item.get("name"), f"section {item['key']}")
        section.is_enabled = item.get("is_enabled", True)
        section.kind = item.get("kind", "listings")
        if section.kind not in SECTION_KINDS:
            raise SeedError(f"section {item['key']}: unknown kind {section.kind!r}")
        section.sort = item.get("sort", i)
        await session.flush()
        report.sections += 1

        # listing tags of the whole section ("for students", "temporary protection"...)
        section_keys = set()
        for attribute in item.get("attributes", []):
            await _upsert_attribute(session, attribute, section=section)
            section_keys.add(attribute["key"])
            report.attributes += 1

        for j, category in enumerate(item.get("categories", []), start=1):
            await _upsert_category(session, report, section, None, category, j, section_keys)

    await session.commit()
    return report
