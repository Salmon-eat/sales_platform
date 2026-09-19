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
