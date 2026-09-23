"""IndexNow: telling search engines about a new or changed page at once, without waiting for a crawl.

Bing, Yandex, Seznam and Naver share one endpoint; Google does not take part (it finds pages through the
sitemap). No account is needed: the site holds a key file at /{key}.txt and signs every ping with that key.
Switched off until INDEXNOW_KEY is set.
"""

import asyncio
import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings

log = logging.getLogger("bazarcito.indexnow")

ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10_000


def _post(payload: dict) -> int:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed https URL)
        return response.status


async def submit(paths: list[str]) -> bool:
    """`paths` are site paths with the language prefix, e.g. /es/empleo/oferta/mozo-almacen-madrid-17."""
    if not settings.indexnow_key or not paths:
        return False
    site = settings.public_site_url.rstrip("/")
    payload = {
        "host": site.removeprefix("https://").removeprefix("http://"),
        "key": settings.indexnow_key,
        "keyLocation": f"{site}/{settings.indexnow_key}.txt",
        "urlList": [f"{site}{p}" if p.startswith("/") else p for p in paths[:MAX_URLS]],
    }
    try:
        status = await asyncio.to_thread(_post, payload)
        log.info("indexnow: %s urls -> %s", len(payload["urlList"]), status)
        return status < 400
    except (OSError, urllib.error.HTTPError) as error:
        log.warning("indexnow failed: %r", error)
        return False
