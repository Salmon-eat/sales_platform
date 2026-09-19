from app.core.slug import slugify, unique_slug


def test_ukrainian_and_russian_transliteration() -> None:
    assert slugify("Водії CE", "uk") == "vodii-ce"
    assert slugify("Водители CE", "ru") == "voditeli-ce"


def test_spanish_accents_are_stripped() -> None:
    assert slugify("A Coruña") == "a-coruna"
    assert slugify("Hostelería") == "hosteleria"


def test_apostrophes() -> None:
    assert slugify("L'Hospitalet de Llobregat") == "l-hospitalet-de-llobregat"
    assert slugify("Кур'єр", "uk") == "kurier"


def test_slugify_never_empty() -> None:
    assert slugify("!!!") == "item"


def test_unique_slug_has_suffix() -> None:
    slug = unique_slug("Conductor CE")
    assert slug.startswith("conductor-ce-")
    assert len(slug) == len("conductor-ce-") + 6
