from typing import Any

LANGS: tuple[str, ...] = ("es", "en", "uk", "ru")
DEFAULT_LANG = "es"


def tr(value: dict[str, Any] | None, lang: str) -> Any:
    """Pick a translation with the spec's fallback: the requested language, then Spanish."""
    if not value:
        return None
    return value.get(lang) or value.get(DEFAULT_LANG) or next(iter(value.values()), None)
