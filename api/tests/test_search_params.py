from app.search.params import AttrSpec, SectionRules, canonical_query, parse_filters
from app.search.text import latin_lookalike, normalize, one_alphabet, tokens

CE_SPECS = {
    "trailer_type": AttrSpec(
        "trailer_type", "multi_enum", ("lona", "frigorifico", "portacoches", "cisterna")
    ),
    "adr": AttrSpec("adr", "bool", ()),
}


def test_unknown_keys_and_values_are_dropped_and_sorted() -> None:
    f = parse_filters(
        {
            "zzz": ["1"],
            "housing": ["1"],
            "schedule": ["shifts,full,bogus"],
            "contract": ["temporal", "indefinido"],
            "posted": ["2y"],
            "salary_min": ["abc"],
            "a.trailer_type": ["frigorifico,lona,boat"],
            "a.unknown": ["1"],
        },
        CE_SPECS,
    )
    assert canonical_query(f) == (
        "a.trailer_type=frigorifico,lona&contract=indefinido,temporal&housing=1&schedule=full,shifts"
    )


CAR_SPECS = {
    "year": AttrSpec("year", "int", ()),
    "km": AttrSpec("km", "int", ()),
    "fuel": AttrSpec("fuel", "enum", ("diesel", "gasolina")),
}


def test_from_to_filters() -> None:
    f = parse_filters(
        {"price": ["8 000-15000"], "a.year": ["2018-"], "a.km": ["-100000"], "a.fuel": ["diesel"]},
        CAR_SPECS,
        rules=SectionRules(price=True),
    )
    assert f.ranges == {"price": (8000, 15000), "a.year": (2018, None), "a.km": (None, 100000)}
    assert canonical_query(f) == "a.fuel=diesel&a.km=-100000&a.year=2018-&price=8000-15000"


def test_from_to_filters_forgive_and_refuse() -> None:
    # the ends the wrong way round are swapped; nonsense and a price on the jobs page are dropped
    raw = {"price": ["15000-8000"], "a.year": ["abc-"], "a.km": ["-"]}
    f = parse_filters(raw, CAR_SPECS, rules=SectionRules(price=True))
    assert f.ranges == {"price": (8000, 15000)}
    assert parse_filters({"price": ["100-200"]}, CAR_SPECS).ranges == {}
    # a number filter is only read for an attribute that is a number
    assert parse_filters({"a.fuel": ["1-2"]}, CAR_SPECS).ranges == {}


def test_job_filters_stay_in_the_jobs_section() -> None:
    # "with housing", "no experience", a salary or a schedule mean nothing on a page of cars
    raw = {
        "housing": ["1"],
        "no_experience": ["1"],
        "salary_min": ["1500"],
        "schedule": ["full"],
        "q": ["seat"],
    }
    assert canonical_query(parse_filters(raw, rules=SectionRules(jobs=False))) == "q=seat"
    assert "housing=1" in canonical_query(parse_filters(raw))


def test_price_sorts() -> None:
    assert canonical_query(parse_filters({"sort": ["price_asc"]})) == "sort=price_asc"
    assert canonical_query(parse_filters({"sort": ["price_desc"]})) == "sort=price_desc"


def test_defaults_are_omitted() -> None:
    assert canonical_query(parse_filters({"sort": ["new"], "page": ["1"]})) == ""
    # with a text query the default sort is relevance
    assert (
        canonical_query(parse_filters({"q": ["  водій   CE "], "sort": ["relevance"]}))
        == "q=%D0%B2%D0%BE%D0%B4%D1%96%D0%B9%20CE"
    )
    assert canonical_query(parse_filters({"q": ["водій"], "sort": ["new"]})).endswith("sort=new")


def test_radius_only_with_a_municipality() -> None:
    assert parse_filters({"radius": ["25"]}).radius is None
    assert parse_filters({"radius": ["25"]}, radius_allowed=True).radius == 25
    assert parse_filters({"radius": ["30"]}, radius_allowed=True).radius is None


def test_tier3_needs_the_category() -> None:
    assert parse_filters({"a.adr": ["1"]}).attrs == {}
    assert parse_filters({"a.adr": ["1"]}, CE_SPECS).attrs == {"adr": True}


def test_page_is_bounded() -> None:
    assert parse_filters({"page": ["99999"]}).page == 100
    assert parse_filters({"page": ["-3"]}).page == 1


def test_text_normalization() -> None:
    assert normalize("  Conductor  CÉ, Frigorífico! ") == "conductor ce frigorifico"
    # "й" is a letter of its own: the ad says "водій", and so must the query
    assert tokens("водій   се  мадрид") == ["водій", "се", "мадрид"]
    assert latin_lookalike("се") == "ce"
    assert latin_lookalike("водій") is None


def test_a_word_typed_on_two_keyboards() -> None:
    """A Spanish and a Ukrainian layout on the same machine: the letters that look the same get mixed."""
    assert one_alphabet("кoмната") == "комната"  # latin "o"
    assert one_alphabet("мaшина") == "машина"  # latin "a"
    # a latin "i" becomes the Ukrainian "і"; turning "діван" into "диван" is the speller's job
    assert one_alphabet("дiван") == "діван"
    assert one_alphabet("диван") is None  # one alphabet already
    assert one_alphabet("bmw") is None
    assert one_alphabet("iphone") is None
