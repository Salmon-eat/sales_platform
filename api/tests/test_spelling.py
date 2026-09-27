"""Repairing a typed word: what it may touch and what it must leave alone."""

from app.search.service import POOR_RESULT, repair_helped
from app.search.spelling import MIN_LENGTH, SIMILAR_ENOUGH
from app.search.text import normalize


def test_the_threshold_is_loose_enough_for_one_wrong_letter() -> None:
    """A single slip in a seven-letter word must stay above the bar, or nothing is ever repaired."""
    assert SIMILAR_ENOUGH <= 0.5
    assert MIN_LENGTH >= 3  # "два", "bmw": too short to guess at


def test_a_ukrainian_word_survives_normalising() -> None:
    """"й" and "ї" are letters, not decorated "и" and "і". An ad says "водій"; if the search box
    turns the same word into "водіи", it no longer matches anything the index holds."""
    assert normalize("Розкладний") == "розкладний"
    assert normalize("Водій") == "водій"
    assert normalize("Київ") == "київ"
    # Russian writes "ё" as "е" half the time, so both spellings have to meet somewhere
    assert normalize("Ёлка") == "елка"


def test_a_correction_has_to_earn_its_place() -> None:
    """Guessing is only allowed to help. A search that already found five ads is never second-guessed,
    and a guess that finds fewer than the visitor's own words is thrown away."""
    assert repair_helped(0, 3)
    assert not repair_helped(5, 1)  # what "водієм" -> "водіи" used to do
    assert not repair_helped(4, 4)  # no gain, no reason to tell anybody anything
    assert POOR_RESULT <= 5  # a full page is never touched


def test_spanish_accents_still_go_away() -> None:
    """Latin marks are decoration: "sofá" and "sofa" are one word, and so are "Málaga" and "Malaga"."""
    assert normalize("Sofá") == "sofa"
    assert normalize("Málaga") == "malaga"
    assert normalize("  dos   palabras ") == "dos palabras"
