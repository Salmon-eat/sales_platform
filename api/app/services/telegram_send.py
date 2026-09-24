"""Sending a short notice through the sign-in bot.

This is the site's own bot (@…LoginBot), never the agency's working bot that takes applications — that
one lives on its own server and this code has no idea it exists.

Telegram only lets a bot write to someone who has opened a chat with it at least once. If they have
not, the API answers 403 and we quietly fall back to email; the person is not told off for it.
"""

import asyncio
import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings

log = logging.getLogger("bazarcito.telegram")

API = "https://api.telegram.org"
TIMEOUT = 10


def _post(chat_id: int, text: str) -> None:
    # plain text on purpose: the notice quotes what a stranger wrote, and no markup means nothing to
    # escape and nothing to abuse
    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    ).encode()
    request = urllib.request.Request(
        f"{API}/bot{settings.telegram_login_token}/sendMessage",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 (fixed https URL)
        response.read()


async def send(chat_id: int, text: str) -> bool:
    """True if Telegram took the message. Never raises: a notice is not worth breaking a job over."""
    if not settings.telegram_login_token:
        return False
    try:
        await asyncio.to_thread(_post, chat_id, text)
        return True
    except urllib.error.HTTPError as error:
        # 403: the person has never opened the bot, so it may not write first. Nothing to fix.
        if error.code == 403:
            log.info("telegram user %s has not started the bot", chat_id)
        else:
            log.warning("telegram refused a message to %s: %s", chat_id, error.code)
        return False
    except OSError as error:
        log.warning("telegram unreachable: %r", error)
        return False
