from typing import Any

LANGS: tuple[str, ...] = ("es", "en", "uk", "ru")
DEFAULT_LANG = "es"


THOUSANDS = {"es": ".", "en": ",", "uk": " ", "ru": " "}


def tr(value: dict[str, Any] | None, lang: str) -> Any:
    """Pick a translation with the spec's fallback: the requested language, then Spanish."""
    if not value:
        return None
    return value.get(lang) or value.get(DEFAULT_LANG) or next(iter(value.values()), None)


def format_number(value: int, lang: str) -> str:
    """189000 -> "189.000" (es), "189,000" (en), "189 000" (uk, ru). Years stay as they are."""
    if value < 10_000:
        return str(value)
    return f"{value:,}".replace(",", THOUSANDS.get(lang, " "))
