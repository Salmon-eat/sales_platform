from app.search.params import AttrSpec, canonical_query, parse_filters
from app.search.text import latin_lookalike, normalize, tokens

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
    assert tokens("водій   се  мадрид") == ["водіи", "се", "мадрид"]
    assert latin_lookalike("се") == "ce"
    assert latin_lookalike("водій") is None
