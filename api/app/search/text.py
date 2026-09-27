import re
import unicodedata

# Cyrillic letters that look like Latin ones: people type "се" meaning "CE".
_HOMOGLYPHS = str.maketrans("асеорхкмтвні", "aceopxkmtbhi")
_WORD = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, accents stripped (á -> a, й -> и, like Postgres unaccent), single spaces."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(_WORD.findall(text))


def tokens(text: str, limit: int = 8) -> list[str]:
    return normalize(text).split()[:limit]


def latin_lookalike(token: str) -> str | None:
    """'се' -> 'ce' for short all-homoglyph Cyrillic tokens (licence categories, codes)."""
    if len(token) <= 3 and token and all(ch in "асеорхкмтвні" for ch in token):
        return token.translate(_HOMOGLYPHS)
    return None


# how many letters at the start of a word we trust to stay put: "Валенсія" and "Валенсії" share four
STEM = 4


def close_enough(typed: str, known: str) -> bool:
    """Is this the same word in a different case ending, or a small typo?

    People write "у Валенсії", not "Валенсія", and "в Малазі", not "Малага"; Spanish and Ukrainian
    endings change the tail of a word while the beginning stays. So: the same first letters, a similar
    length, and at most one or two letters different overall.
    """
    if typed == known:
        return True
    if len(typed) < 5 or len(known) < 5 or typed[:STEM] != known[:STEM]:
        return False
    if abs(len(typed) - len(known)) > 2:
        return False
    # "малазі" / "малага" differ by two letters and are six long, so six already allows two
    allowed = 1 if min(len(typed), len(known)) < 6 else 2
    return _distance(typed, known, allowed) <= allowed


def _distance(a: str, b: str, limit: int) -> int:
    """Levenshtein, stopped as soon as it is clearly over the limit."""
    previous = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, start=1):
        current = [i]
        for j, ch_b in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ch_a != ch_b))
            )
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]
