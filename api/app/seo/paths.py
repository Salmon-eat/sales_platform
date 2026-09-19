"""URL building blocks shared by the resolver, cards, suggest and sitemaps.

    /{lang}/{section}/{sector?}/{profession?}/{feature?}/{location?}     list pages (L1–L3)
    /{lang}/{section}/{offer word}/{slug}-{id}                           listing card (L4)

Paths returned by the API have no language prefix: the web app adds /es, /en, /ua, /ru.
"""

import re

LANGS = ("es", "en", "uk", "ru")

# spec §6 example uses "oferta"; the word is translated like the other service words
OFFER_WORD = {"es": "oferta", "en": "job", "uk": "vakansiia", "ru": "vakansiya"}

# tier-2 filters lifted into the path (spec §6, "second stage"): at most one, between category and location
FEATURES: dict[str, dict[str, str]] = {
    "housing": {"es": "con-alojamiento", "en": "with-housing", "uk": "z-zhytlom", "ru": "s-zhilyom"},
}

_LISTING_TAIL = re.compile(r"^(?P<slug>[a-z0-9-]*?)-?(?P<id>\d+)$")


def list_path(*segments: str | None) -> str:
    return "/".join(s for s in segments if s)


def listing_path(section_slug: str, lang: str, slug: str, listing_id: int) -> str:
    return f"{section_slug}/{OFFER_WORD[lang]}/{slug}-{listing_id}"


def parse_listing_tail(segment: str) -> tuple[str, int] | None:
    """'conductor-ce-frigorifico-madrid-12345' -> ('conductor-ce-frigorifico-madrid', 12345)."""
    match = _LISTING_TAIL.match(segment)
    return (match["slug"], int(match["id"])) if match else None


def feature_by_slug(slug: str) -> tuple[str, str] | None:
    """-> (feature key, language of the slug)."""
    for key, slugs in FEATURES.items():
        for lang, value in slugs.items():
            if value == slug:
                return key, lang
    return None


def offer_word_lang(segment: str) -> str | None:
    return next((lang for lang, word in OFFER_WORD.items() if word == segment), None)
