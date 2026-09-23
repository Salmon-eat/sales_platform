"""Sending email: sign-in codes now, notifications later.

Two ways, chosen by the settings: Resend (an HTTPS request, nothing to install) or a plain SMTP server.
With neither configured — local development — the letter is written to the log instead of being sent, so
the sign-in code is visible in the console.
"""

import asyncio
import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("bazarcito.mail")

RESEND_URL = "https://api.resend.com/emails"


def _send_resend(to: str, subject: str, text: str) -> None:
    payload = json.dumps({"from": settings.mail_from, "to": [to], "subject": subject, "text": text}).encode()
    request = urllib.request.Request(
        RESEND_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed https URL)
        response.read()


def _send_smtp(to: str, subject: str, text: str) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


async def send(to: str, subject: str, text: str) -> bool:
    """True if the letter left the building. Failures are logged, never raised at the visitor."""
    if settings.resend_api_key:
        sender = _send_resend
    elif settings.smtp_host:
        sender = _send_smtp
    else:
        log.warning("email not configured; letter to %s:\n%s\n%s", to, subject, text)
        return False
    try:
        await asyncio.to_thread(sender, to, subject, text)
        return True
    except (OSError, urllib.error.HTTPError, smtplib.SMTPException) as error:
        log.error("could not send email to %s: %r", to, error)
        return False
