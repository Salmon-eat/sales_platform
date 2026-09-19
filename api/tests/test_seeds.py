"""Data checks for seeds/ that run in CI without a database."""

import json
from collections import Counter

from app.core.slug import slugify
from app.importers.locations import OVERRIDES_FILE, REGIONS_FILE
from app.importers.taxonomy import ATTRIBUTE_TYPES, load_seed
from app.models.i18n import LANGS

SLUG_RE = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def _walk(categories, parent=None):  # noqa: ANN001, ANN202
    for category in categories:
        yield category, parent
        yield from _walk(category.get("children", []), category)


def test_taxonomy_translations_and_slugs() -> None:
    import re

    data = load_seed()
    for section in data["sections"]:
        assert set(section["slug"]) == set(LANGS) and set(section["name"]) == set(LANGS)
        seen = {lang: Counter() for lang in LANGS}
        for category, parent in _walk(section["categories"]):
            where = category["slug"].get("es")
            assert all(category["slug"].get(lang) for lang in LANGS), f"{where}: slug translations"
            assert all(category["name"].get(lang) for lang in LANGS), f"{where}: name translations"
            for lang in LANGS:
                assert re.match(SLUG_RE, category["slug"][lang]), f"{where}: bad {lang} slug"
                seen[lang][category["slug"][lang]] += 1
            assert parent is None or not category.get("children"), f"{where}: too deep"
            for attr in category.get("attributes", []):
                assert attr["type"] in ATTRIBUTE_TYPES
                assert all(attr["label"].get(lang) for lang in LANGS)
                for option in attr.get("options", []):
                    assert all(option["label"].get(lang) for lang in LANGS), (
                        f"{attr['key']}.{option['value']}"
                    )
        duplicates = {lang: [s for s, n in c.items() if n > 1] for lang, c in seen.items()}
        assert not any(duplicates.values()), f"duplicate slugs in {section['key']}: {duplicates}"


def test_category_slugs_do_not_clash_with_regions() -> None:
    regions = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    region_slugs = {f"comunidad-{c['slug']}" for c in regions["comunidades"]} | {
        f"provincia-{p['slug']}" for p in regions["provincias"]
    }
    category_slugs = {
        slug
        for section in load_seed()["sections"]
        for category, _ in _walk(section["categories"])
        for slug in category["slug"].values()
    }
    assert not category_slugs & region_slugs


def test_regions_are_complete() -> None:
    regions = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    assert len(regions["comunidades"]) == 19
    assert len(regions["provincias"]) == 52
    for item in regions["comunidades"] + regions["provincias"]:
        assert all(item["names"].get(lang) for lang in LANGS), item["code"]
        assert slugify(item["slug"]) == item["slug"]


def test_overrides_are_well_formed() -> None:
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))["municipios"]
    for code, override in overrides.items():
        if code.startswith("_"):
            continue
        assert len(code) == 5 and code.isdigit(), code
        assert override.get("expect"), f"{code}: 'expect' guards against a wrong INE code"
        assert set(override) <= {"expect", "es", "en", "uk", "ru", "aliases", "geonames_id", "coords_near"}
