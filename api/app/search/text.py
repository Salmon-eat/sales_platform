import re
import unicodedata

# Cyrillic letters that look like Latin ones: people type "се" meaning "CE".
_HOMOGLYPHS = str.maketrans("асеорхкмтвні", "aceopxkmtbhi")
_WORD = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, Latin accents stripped (á -> a), single spaces.

    Marks are only stripped from Latin letters. In Spanish "sofá" and "sofa" are the same word, but
    in Ukrainian "й" is not "и" and "ї" is not "і" — they are separate letters, and an ad that says
    "водій" is stored with the "й". Stripping it turned every query into a word the index does not
    contain, and the site could only ever find such ads by approximate match.

    "ё" is the exception: Russian writes it as "е" half the time, so both sides become "е".
    """
    text = text.lower().replace("ё", "е")
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", text):
        if unicodedata.combining(ch) and out and out[-1].isascii():
            continue  # "á" -> "a"
        out.append(ch)
    return " ".join(_WORD.findall(unicodedata.normalize("NFC", "".join(out))))


def tokens(text: str, limit: int = 8) -> list[str]:
    return normalize(text).split()[:limit]


# words that say nothing about what is wanted: every ad in the section is "work", every page is a
# "job offer". Four languages, because the site has four.
STOPWORDS = {
    "в", "у", "на", "з", "із", "по", "робота", "роботу", "вакансія", "вакансії", "вакансия", "вакансии",
    "работа", "работу", "во", "trabajo", "empleo", "oferta", "ofertas", "de", "en", "el", "la",
    "job", "jobs", "work", "in", "at", "spain", "espana", "іспанія", "іспанії", "испания", "испании",
}  # fmt: skip


def meaningful(text: str) -> list[str]:
    """The words worth matching on. "робота водієм" is a search for a driver, not for the word "робота";
    keeping it turned a search that should find five ads into one. A query made of nothing but such
    words ("робота") keeps them — it is all the visitor gave us."""
    words = tokens(text)
    kept = [w for w in words if w not in STOPWORDS]
    return kept or words


def latin_lookalike(token: str) -> str | None:
    """'се' -> 'ce' for short all-homoglyph Cyrillic tokens (licence categories, codes)."""
    if len(token) <= 3 and token and all(ch in "асеорхкмтвні" for ch in token):
        return token.translate(_HOMOGLYPHS)
    return None


_TO_CYRILLIC = str.maketrans("aceopxkmtbhi", "асеорхкмтвні")


def one_alphabet(token: str) -> str | None:
    """"дiван" with a Latin "i" in the middle: one word typed on two keyboard layouts.

    People here switch between a Spanish and a Ukrainian keyboard all day, and the letters that look
    the same get mixed. Only a word that really contains both alphabets is touched — "bmw" and
    "диван" are left exactly as they were.
    """
    has_cyrillic = any("Ѐ" <= ch <= "ӿ" for ch in token)
    has_latin = any("a" <= ch <= "z" for ch in token)
    if not (has_cyrillic and has_latin):
        return None
    together = token.translate(_TO_CYRILLIC)
    return together if together != token else None


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


def close_by_edits(typed: str, known: str) -> bool:
    """One slip in a short word, two in a long one — the bar every search engine uses.

    Trigram similarity alone misses the commonest mistake of all: "leptop" and "laptop" share only
    0.40 of their trigrams, below any threshold loose enough to be safe, yet they are one keystroke
    apart. Counting the keystrokes catches it without loosening anything else.
    """
    allowed = 1 if len(typed) < 8 else 2
    if abs(len(typed) - len(known)) > allowed:
        return False
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
