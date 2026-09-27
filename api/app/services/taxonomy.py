from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttributeDefinition, Category, Section
from app.models.i18n import tr
from app.schemas.taxonomy import (
    AdminAttribute,
    AdminCategory,
    AdminSection,
    AttributeOption,
    AttributeOut,
    CategoryNode,
    SectionOut,
    TaxonomyOut,
)


async def _load(session: AsyncSession, enabled_only: bool):  # noqa: ANN202
    sections = (await session.scalars(select(Section).order_by(Section.sort, Section.id))).all()
    stmt = select(Category).order_by(Category.sort, Category.id)
    if enabled_only:
        stmt = stmt.where(Category.is_enabled)
    categories = (await session.scalars(stmt)).all()
    attributes = (
        await session.scalars(select(AttributeDefinition).order_by(AttributeDefinition.facet_order))
    ).all()

    attrs_by_category: dict[int, list[AttributeDefinition]] = defaultdict(list)
    attrs_by_section: dict[int, list[AttributeDefinition]] = defaultdict(list)
    for attr in attributes:
        if attr.section_id is not None:
            attrs_by_section[attr.section_id].append(attr)
        else:
            attrs_by_category[attr.category_id].append(attr)  # type: ignore[index]
    children: dict[int | None, list[Category]] = defaultdict(list)
    for category in categories:
        children[category.parent_id].append(category)
    return sections, children, attrs_by_category, attrs_by_section


def _attribute_out(attr: AttributeDefinition, lang: str) -> AttributeOut:
    return AttributeOut(
        key=attr.key,
        type=attr.type,
        label=tr(attr.label, lang),
        unit=tr(attr.unit, lang) if attr.unit else None,
        options=[AttributeOption(value=o["value"], label=tr(o["label"], lang)) for o in attr.options],
        filterable=attr.filterable,
        facet_order=attr.facet_order,
        required=attr.required,
        seo_indexable=attr.seo_indexable,
        defined_on=attr.category_id,
    )


async def build_taxonomy(session: AsyncSession, lang: str) -> TaxonomyOut:
    sections, children, attrs, section_attrs = await _load(session, enabled_only=True)

    def node(category: Category, inherited: list[AttributeOut]) -> CategoryNode:
        own = [_attribute_out(a, lang) for a in attrs[category.id]]
        effective = sorted([*inherited, *own], key=lambda a: a.facet_order)
        return CategoryNode(
            id=category.id,
            slug=category.slug[lang],
            slugs=category.slug,
            name=tr(category.name, lang),
            icon=category.icon,
            synonyms=category.synonyms.get(lang, []),
            attributes=effective,
            children=[node(child, effective) for child in children[category.id]],
        )

    return TaxonomyOut(
        sections=[
            SectionOut(
                key=s.key,
                slug=s.slug[lang],
                slugs=s.slug,
                name=tr(s.name, lang),
                is_enabled=s.is_enabled,
                kind=s.kind,
                attributes=[_attribute_out(a, lang) for a in section_attrs[s.id]],
                categories=[node(c, []) for c in children[None] if c.section_id == s.id],
            )
            for s in sections
        ]
    )


async def build_admin_taxonomy(session: AsyncSession) -> list[AdminSection]:
    sections, children, attrs, section_attrs = await _load(session, enabled_only=False)

    def node(category: Category) -> AdminCategory:
        return AdminCategory(
            id=category.id,
            parent_id=category.parent_id,
            slug=category.slug,
            name=category.name,
            synonyms=category.synonyms,
            icon=category.icon,
            sort=category.sort,
            is_enabled=category.is_enabled,
            attributes=[AdminAttribute.model_validate(a, from_attributes=True) for a in attrs[category.id]],
            children=[node(child) for child in children[category.id]],
        )

    return [
        AdminSection(
            id=s.id,
            key=s.key,
            slug=s.slug,
            name=s.name,
            is_enabled=s.is_enabled,
            kind=s.kind,
            sort=s.sort,
            attributes=[AdminAttribute.model_validate(a, from_attributes=True) for a in section_attrs[s.id]],
            categories=[node(c) for c in children[None] if c.section_id == s.id],
        )
        for s in sections
    ]
