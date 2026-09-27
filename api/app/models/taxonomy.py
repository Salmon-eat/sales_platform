from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

Localized = dict[str, str]


SECTION_KINDS = ("listings", "services")


class Section(Base):
    """Top level: empleo, servicios, vivienda. Enabled/disabled by data, not code.

    kind = listings: vacancies/ads published and closed by managers (Робота, Житло);
    kind = services: permanent services of the agency (documents, training): content pages with an
    application form, never listings."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default="listings", server_default="listings")
    slug: Mapped[Localized] = mapped_column(JSONB)
    name: Mapped[Localized] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(default=True, server_default="true")
    sort: Mapped[int] = mapped_column(default=0, server_default="0")

    categories: Mapped[list["Category"]] = relationship(back_populates="section", lazy="raise")


class Category(Base):
    """Sector (parent_id NULL) or profession (parent = sector)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="RESTRICT"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    slug: Mapped[Localized] = mapped_column(JSONB)
    name: Mapped[Localized] = mapped_column(JSONB)
    synonyms: Mapped[dict[str, list[str]]] = mapped_column(JSONB, default=dict, server_default="{}")
    # words added from the admin, kept apart from the seed file so seeding never wipes them
    extra_synonyms: Mapped[dict[str, list[str]]] = mapped_column(JSONB, default=dict, server_default="{}")
    icon: Mapped[str | None] = mapped_column(String(50))
    sort: Mapped[int] = mapped_column(default=0, server_default="0")
    is_enabled: Mapped[bool] = mapped_column(default=True, server_default="true")
    seo_text: Mapped[Localized] = mapped_column(JSONB, default=dict, server_default="{}")

    section: Mapped[Section] = relationship(back_populates="categories", lazy="raise")
    attributes: Mapped[list["AttributeDefinition"]] = relationship(lazy="raise")


class AttributeDefinition(Base):
    """Listing attribute defined either on a category (tier-3 filter, inherited by child categories)
    or on a whole section (listing tags such as "for students", "temporary protection": tier-2 filters
    shown in the whole section). Exactly one of category_id / section_id is set."""

    __tablename__ = "attribute_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(20))  # bool | enum | multi_enum | int_range
    label: Mapped[Localized] = mapped_column(JSONB)
    # [{"value": "frigorifico", "label": {"es": ..., "en": ..., "uk": ..., "ru": ...}}]
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    filterable: Mapped[bool] = mapped_column(default=True, server_default="true")
    facet_order: Mapped[int] = mapped_column(default=0, server_default="0")
    required: Mapped[bool] = mapped_column(default=False, server_default="false")
    seo_indexable: Mapped[bool] = mapped_column(default=False, server_default="false")
