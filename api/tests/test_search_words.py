"""Words with different endings, and what stops a common word from becoming a village.

Two separate things are at work: `close_enough` says "this is the same word with another tail", and
the dictionary only offers it towns people actually search for. The first one is deliberately loose;
the second is what keeps "ремонт" from turning into the village of Remondo.
"""

import pytest

from app.search.text import close_enough
from app.search.understanding import FUZZY_MIN_POPULATION, PlaceEntry, _by_stem, _similar


@pytest.mark.parametrize(
    ("typed", "known"),
    [
        ("валенсii", "валенсiя"),  # accents are already stripped by normalize()
        ("мадридi", "мадрид"),
        ("барселонi", "барселона"),
        ("малазi", "малага"),
        ("ремонту", "ремонт"),
        ("дивани", "диван"),
    ],
)
def test_the_same_word_with_another_ending(typed: str, known: str) -> None:
    assert close_enough(typed, known)


@pytest.mark.parametrize(
    ("typed", "known"),
    [
        ("мадрид", "мурсия"),  # nothing in common but the length
        ("салон", "талон"),  # a different first letter is a different word
        ("работа", "ворота"),
        ("диван", "стол"),
    ],
)
def test_words_that_only_look_similar(typed: str, known: str) -> None:
    assert not close_enough(typed, known)


def a_place(name: str, population: int) -> PlaceEntry:
    return PlaceEntry(id=1, level="municipio", slug=name, names={"uk": name}, population=population)


def test_a_village_never_swallows_a_common_word() -> None:
    """"Ремонт" and "Ремондо" are one letter apart; only one of them is a place anybody searches for."""
    places = {
        "ремондо": a_place("ремондо", 200),
        "малага": a_place("малага", 570_000),
    }
    grouped = _by_stem(places, FUZZY_MIN_POPULATION)

    assert _similar("ремонт", grouped) is None
    assert _similar("малазi", grouped) == "малага"


def test_without_the_population_floor_the_village_would_match() -> None:
    """The floor is doing the work here, not the word comparison — this is what it protects against."""
    grouped = _by_stem({"ремондо": a_place("ремондо", 200)})
    assert _similar("ремонт", grouped) == "ремондо"
