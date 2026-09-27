from app.search.text import normalize
from app.search.understanding import CategoryEntry, Dictionary, PlaceEntry, understand

CE = dict(id=2, section_id=1, section_key="empleo", parent_id=1, slug={"es": "conductor-ce", "uk": "vodii-ce"},  # noqa: E501
          name={"es": "Conductor CE", "uk": "Водій CE"})  # fmt: skip
CAMARERO = dict(id=14, section_id=1, section_key="empleo", parent_id=13, slug={"es": "camarero", "uk": "ofitsiant"},  # noqa: E501
                name={"es": "Camarero", "uk": "Офіціант"})  # fmt: skip
MADRID = PlaceEntry(1, "municipio", "madrid", {"es": "Madrid", "uk": "Мадрид"}, 3_000_000)
VALENCIA_CITY = PlaceEntry(2, "municipio", "valencia", {"es": "Valencia"}, 800_000)


def _dictionary() -> Dictionary:
    categories: dict[str, list[CategoryEntry]] = {}
    for data, synonyms in ((CE, ["водій", "фура", "camionero"]), (CAMARERO, ["mesero"])):
        for phrase in data["name"].values():
            categories.setdefault(normalize(phrase), []).append(CategoryEntry(**data, is_name=True))
        for phrase in synonyms:
            categories.setdefault(normalize(phrase), []).append(CategoryEntry(**data, is_name=False))
    places = {"madrid": MADRID, "мадрид": MADRID, "valencia": VALENCIA_CITY, "валенсия": VALENCIA_CITY}
    by_id = {2: CategoryEntry(**CE, is_name=True), 14: CategoryEntry(**CAMARERO, is_name=True)}
    return Dictionary(categories, places, by_id, "1", 0.0)


def test_profession_and_city_with_cyrillic_lookalikes() -> None:
    u = understand(_dictionary(), "водій се мадрид")
    assert u.category and u.category.slug["es"] == "conductor-ce"
    assert u.place == MADRID
    assert u.complete


def test_rest_goes_to_full_text() -> None:
    u = understand(_dictionary(), "camionero frigorifico valencia")
    assert u.category and u.category.id == 2
    assert u.place == VALENCIA_CITY
    assert u.rest == "frigorifico"
    assert not u.complete


def test_stopwords_are_dropped_only_with_entities() -> None:
    assert understand(_dictionary(), "робота офіціант в мадрид").complete
    plain = understand(_dictionary(), "робота мрії")
    assert plain.category is None and plain.rest == "робота мрії"


def test_short_tokens_are_not_places() -> None:
    dictionary = _dictionary()
    dictionary.places["el"] = PlaceEntry(9, "municipio", "el", {"es": "El"}, 10)
    assert understand(dictionary, "el camarero").place is None
