from app.importers.locations import (
    ImportReport,
    IneMunicipality,
    Row,
    assign_municipality_slugs,
    clean_aliases,
    fix_article,
    norm,
)


def test_fix_article() -> None:
    assert fix_article("Coruña, A") == "A Coruña"
    assert fix_article("Palmas de Gran Canaria, Las") == "Las Palmas de Gran Canaria"
    assert fix_article("Hospitalet de Llobregat, L'") == "L'Hospitalet de Llobregat"
    assert fix_article("Camp de Mirra, el") == "El Camp de Mirra"
    # a comma that is not an article stays as is
    assert fix_article("Saus, Camallera i Llampaies") == "Saus, Camallera i Llampaies"


def test_norm_ignores_case_and_accents() -> None:
    assert norm("València") == norm("VALENCIA") == "valencia"


def test_clean_aliases_dedupes_and_drops_the_main_name() -> None:
    assert clean_aliases(["Alicante", "Alacant", "alacant", "", "03014"], exclude="Alicante") == ["Alacant"]


def _row(code: str, name: str, province: str, population: int) -> Row:
    return Row("municipio", code, province, "", {"es": name}, [], population, 0.0, 0.0)


def test_slug_collisions_keep_the_biggest_plain() -> None:
    big, small = _row("45001", "Villanueva", "45", 5000), _row("13001", "Villanueva", "13", 300)
    other = _row("28001", "Transporte", "28", 100)
    report = ImportReport()

    assign_municipality_slugs(
        [small, big, other],
        reserved={"transporte"},
        province_slugs={"45": "toledo", "13": "ciudad-real", "28": "madrid"},
        existing_slugs={},
        report=report,
    )

    assert big.slug == "villanueva"
    assert small.slug == "villanueva-ciudad-real"
    assert other.slug == "transporte-madrid"  # reserved by a category
    assert len(report.slug_collisions) == 2


def test_existing_slugs_are_kept() -> None:
    row = _row("45001", "Villanueva", "45", 5000)
    row.slug = "old-slug"
    assign_municipality_slugs(
        [row], set(), {"45": "toledo"}, {("municipio", "45001"): "old-slug"}, ImportReport()
    )
    assert row.slug == "old-slug"


def test_ine_municipality_parts_example() -> None:
    m = IneMunicipality("03014", "10", "03", "Alacant/Alicante", ["Alacant", "Alicante"])
    assert m.parts[1] == "Alicante"
