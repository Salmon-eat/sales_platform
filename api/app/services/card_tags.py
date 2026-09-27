"""Short features on listing cards ("We speak Ukrainian", "Code 95", "Meals"), built from the listing's
attributes and their dictionary labels, so they are always in the page language."""

import re
from typing import Any

from app.models import AttributeDefinition, Listing
from app.models.i18n import format_number, tr
from app.schemas.listing import CardTag

# the order people scan a card in: can I talk there, are my papers fine, what do I get, is it for me
KIND = {
    "team_language": "lang",
    "spanish_level": "lang",
    "english_level": "lang",
    "documents": "doc",
    "official": "ok",
    "benefits": "perk",
    "suitable_for": "info",
}
ORDER = list(KIND)
# a car is read make first, then year and kilometres, then the rest
LEADING = ["brand", "year", "km", "fuel", "gearbox", "body"]
SKIP = {"housing_cost"}  # merged into the "housing" tag by the card itself
LOWERCASE_LANGS = {"uk", "ru", "es"}  # language names are not capitalized mid-sentence there


def _short(label: str) -> str:
    """'ADR (dangerous goods)' -> 'ADR' on a small card."""
    return re.sub(r"\s*\(.*\)$", "", label).strip()


def _option(defn: AttributeDefinition, value: Any, lang: str) -> str | None:
    for option in defn.options:
        if option.get("value") == value:
            return tr(option.get("label"), lang)
    return None


def card_tags(listing: Listing, definitions: list[AttributeDefinition], lang: str) -> list[CardTag]:
    attrs = listing.attributes or {}
    by_key = {d.key: d for d in definitions}
    keys = (
        [k for k in LEADING if k in attrs]
        + [k for k in ORDER if k in attrs]
        + [k for k in attrs if k not in KIND and k not in SKIP and k not in LEADING]
    )
    tags: list[CardTag] = []
    for key in keys:
        defn, value = by_key.get(key), attrs[key]
        if defn is None or value in (None, False, "", []):
            continue
        kind = KIND.get(key, "info")
        label = tr(defn.label, lang)
        if key == "team_language":
            names = [n for v in value if (n := _option(defn, v, lang))]
            if lang in LOWERCASE_LANGS:
                names = [n.lower() for n in names]
            if names:
                tags.append(CardTag(key=key, label=f"{label} {', '.join(names)}", kind="lang"))
        elif key in ("spanish_level", "english_level"):
            tags.append(CardTag(key=key, label=f"{label}: {str(value).upper()}", kind="lang"))
        elif defn.type == "bool":
            tags.append(CardTag(key=key, label=_short(label), kind=kind))
        elif defn.type == "multi_enum" and isinstance(value, list):
            tags += [
                CardTag(key=f"{key}.{v}", label=name, kind=kind)
                for v in value
                if (name := _option(defn, v, lang))
            ]
        elif defn.type == "int" and isinstance(value, int):
            # "189 000 km" says what it is by its unit; a bare year says it by itself
            unit = tr(defn.unit, lang) if defn.unit else None
            text = f"{format_number(value, lang)} {unit}" if unit else format_number(value, lang)
            tags.append(CardTag(key=key, label=text, kind=kind))
        elif defn.type == "enum" and (name := _option(defn, value, lang)):
            # "3/1" alone says nothing: short values get the field name; a make ("Ford", "MG") is
            # recognised by itself
            text = f"{_short(label)}: {name}" if len(name) <= 4 and key != "brand" else name
            tags.append(CardTag(key=key, label=text, kind=kind))
    housing_cost = by_key.get("housing_cost")
    if listing.housing and housing_cost and (name := _option(housing_cost, attrs.get("housing_cost"), lang)):
        tags.insert(0, CardTag(key="housing_cost", label=name, kind="ok"))
    return tags
