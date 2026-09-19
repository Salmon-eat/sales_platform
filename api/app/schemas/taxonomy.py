from typing import Any

from pydantic import BaseModel, Field

Localized = dict[str, str]


# ---------- public: one language ----------


class AttributeOption(BaseModel):
    value: str
    label: str


class AttributeOut(BaseModel):
    key: str
    type: str
    label: str
    options: list[AttributeOption]
    filterable: bool
    facet_order: int
    required: bool
    seo_indexable: bool
    defined_on: int | None = Field(
        description="category id where the attribute is defined (may be a parent); null for section tags"
    )


class CategoryNode(BaseModel):
    id: int
    slug: str
    slugs: Localized
    name: str
    icon: str | None
    synonyms: list[str]
    attributes: list[AttributeOut] = Field(description="own + inherited from the parent sector")
    children: list["CategoryNode"] = Field(default_factory=list)


class SectionOut(BaseModel):
    key: str
    slug: str
    slugs: Localized
    name: str
    is_enabled: bool
    kind: str = Field(description="listings (vacancies, ads) or services (permanent agency services)")
    attributes: list[AttributeOut] = Field(description="listing tags of the whole section")
    categories: list[CategoryNode]


class TaxonomyOut(BaseModel):
    sections: list[SectionOut]


# ---------- admin: every language ----------


class AdminAttribute(BaseModel):
    id: int
    key: str
    type: str
    label: Localized
    options: list[dict[str, Any]]
    filterable: bool
    facet_order: int
    required: bool
    seo_indexable: bool


class AdminCategory(BaseModel):
    id: int
    parent_id: int | None
    slug: Localized
    name: Localized
    synonyms: dict[str, list[str]]
    icon: str | None
    sort: int
    is_enabled: bool
    attributes: list[AdminAttribute]
    children: list["AdminCategory"] = Field(default_factory=list)


class AdminSection(BaseModel):
    id: int
    key: str
    slug: Localized
    name: Localized
    is_enabled: bool
    kind: str = Field(description="listings (vacancies, ads) or services (permanent agency services)")
    sort: int
    attributes: list[AdminAttribute] = Field(description="listing tags of the whole section")
    categories: list[AdminCategory]
