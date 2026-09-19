import re
import secrets
import unicodedata

# Ukrainian national transliteration (simplified: no position-dependent rules).
_UK = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ю": "iu",
    "я": "ia", "'": "", "’": "", "ʼ": "",
}  # fmt: skip

# Russian: common "passport-style" transliteration.
_RU = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}  # fmt: skip


def transliterate(value: str, lang: str = "es") -> str:
    """Lowercase ASCII text: Cyrillic by language rules, Latin accents stripped. Keeps spaces."""
    table = _RU if lang == "ru" else _UK
    # Latin elision (L'Hospitalet) separates words; a Cyrillic apostrophe (Кур'єр) is dropped by the table.
    text = re.sub(r"(?<=[a-z])['’](?=[a-z])", " ", value.lower())
    text = "".join(table.get(ch, ch) for ch in text)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def slugify(value: str, lang: str = "es") -> str:
    """Latin-only slug. Cyrillic is transliterated by language rules, Latin accents are stripped
    (A Coruña -> a-coruna)."""
    return re.sub(r"[^a-z0-9]+", "-", transliterate(value, lang)).strip("-") or "item"


def unique_slug(value: str, lang: str = "es") -> str:
    return f"{slugify(value, lang)[:100].rstrip('-')}-{secrets.token_hex(3)}"
