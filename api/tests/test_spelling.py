"""Repairing a typed word: what it may touch and what it must leave alone."""

from app.search.spelling import MIN_LENGTH, SIMILAR_ENOUGH
from app.search.text import normalize


def test_the_threshold_is_loose_enough_for_one_wrong_letter() -> None:
    """A single slip in a seven-letter word must stay above the bar, or nothing is ever repaired."""
    assert SIMILAR_ENOUGH <= 0.5
    assert MIN_LENGTH >= 3  # "два", "bmw": too short to guess at


def test_words_are_stored_the_way_a_query_is_read() -> None:
    """The vocabulary and the search box have to agree on spelling, or the site "corrects" a word
    that was right: "розкладний" typed becomes "розкладнии" after normalising, and the stored word
    must have gone through exactly the same door."""
    # "й" is "и" with a mark on top, and stripping marks is what makes accents irrelevant elsewhere
    assert normalize("Розкладний") == "розкладнии"
    assert normalize("Málaga") == "malaga"
    assert normalize("  двоє   слів ") == "двоє слів"
