"""Which attribute definitions apply to a listing or a search: the section's tags + the category's own
and inherited ones. The single place for this rule (listing form, validation, search, card page)."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttributeDefinition, Category


async def attribute_definitions(
    session: AsyncSession,
    *,
    section_id: int | None,
    category: Category | None,
    filterable_only: bool = False,
) -> list[AttributeDefinition]:
    """Section tags first (tier 2), then category attributes (tier 3), each by facet_order."""
    owners = []
    if section_id is not None:
        owners.append(AttributeDefinition.section_id == section_id)
    if category is not None:
        ids = [category.id] + ([category.parent_id] if category.parent_id else [])
        owners.append(AttributeDefinition.category_id.in_(ids))
    if not owners:
        return []
    stmt = select(AttributeDefinition).where(or_(*owners))
    if filterable_only:
        stmt = stmt.where(AttributeDefinition.filterable)
    rows = (await session.scalars(stmt)).all()
    return sorted(rows, key=lambda a: (a.section_id is None, a.facet_order, a.id))
