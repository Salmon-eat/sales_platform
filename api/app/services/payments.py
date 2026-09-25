"""Paying for an extra, and switching it on once the money is there.

Two ways in: a card through Stripe, or the team marking a transfer as received. Both end in the same
place — `mark_paid`, which is the only function that switches anything on, and only once.

Stripe is called over plain HTTPS: one endpoint to open a checkout page, one signature to check when
it calls back. That is less to keep up to date than a whole SDK.
"""

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Company, Listing, Order, User
from app.services import pricing

log = logging.getLogger("bazarcito.payments")

STRIPE_API = "https://api.stripe.com/v1/checkout/sessions"
TIMEOUT = 15
# a callback older than this is not worth trusting
WEBHOOK_TOLERANCE = 300


async def create(session: AsyncSession, user: User, product_key: str, target_id: int) -> Order:
    """An order is written down first; nothing is switched on until it is paid."""
    try:
        product = pricing.get(product_key)
    except KeyError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_product") from exc

    listing_id = company_id = None
    if product.target == "listing":
        listing = await session.get(Listing, target_id)
        if listing is None or listing.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
        if listing.status != "active":
            # paying to raise an ad nobody can see would be taking money for nothing
            raise HTTPException(status.HTTP_409_CONFLICT, "listing_not_active")
        listing_id = listing.id
    else:
        company = await session.get(Company, target_id)
        if company is None or company.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
        if company.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "company_not_active")
        company_id = company.id

    order = Order(
        user_id=user.id,
        listing_id=listing_id,
        company_id=company_id,
        product=product.key,
        days=product.days,
        amount=product.amount,
        currency=pricing.CURRENCY,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def mark_paid(
    session: AsyncSession, order: Order, provider: str, reference: str | None = None
) -> Order:
    """The one place where anything is switched on, and only the first time."""
    if order.applied_at is not None:
        return order
    now = datetime.now(UTC)
    order.status, order.provider, order.provider_ref = "paid", provider, reference
    order.paid_at = order.paid_at or now
    await _apply(session, order, now)
    order.applied_at = now
    await session.commit()
    await session.refresh(order)
    return order


async def _apply(session: AsyncSession, order: Order, now: datetime) -> None:
    """Giving the buyer what they paid for; time bought adds onto time already there."""
    if order.listing_id:
        listing = await session.get(Listing, order.listing_id)
        if listing is None:
            log.warning("order %s paid for a listing that is gone", order.id)
            return
        if order.product == "bump":
            listing.bumped_at = now
        elif order.product == "highlight_7":
            listing.highlighted_until = _extend(listing.highlighted_until, order.days, now)
        elif order.product == "top_7":
            listing.promoted_until = _extend(listing.promoted_until, order.days, now)
    elif order.company_id:
        company = await session.get(Company, order.company_id)
        if company is None:
            log.warning("order %s paid for a company that is gone", order.id)
            return
        company.promoted_until = _extend(company.promoted_until, order.days, now)


def _extend(current: datetime | None, days: int, now: datetime) -> datetime:
    base = current if current and current > now else now
    return base + timedelta(days=days)


async def my_orders(session: AsyncSession, user: User) -> list[Order]:
    rows = await session.scalars(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(50)
    )
    return list(rows.all())


# ---------------------------------------------------------------------------- the card


def configured() -> bool:
    return bool(settings.stripe_secret_key)


def _post(url: str, fields: list[tuple[str, str]]) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 (fixed https URL)
        return json.loads(response.read().decode())


def checkout_fields(order: Order, name: str, success_url: str, cancel_url: str) -> list[tuple[str, str]]:
    return [
        ("mode", "payment"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("client_reference_id", str(order.id)),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", order.currency.lower()),
        ("line_items[0][price_data][unit_amount]", str(order.amount)),
        ("line_items[0][price_data][product_data][name]", name),
        ("metadata[order_id]", str(order.id)),
    ]


async def checkout_url(order: Order, name: str, success_url: str, cancel_url: str) -> str:
    """Stripe's own page takes the card details; they never touch our server."""
    if not configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "payments_not_configured")
    try:
        data = _post(STRIPE_API, checkout_fields(order, name, success_url, cancel_url))
    except urllib.error.HTTPError as error:
        log.error("stripe refused a checkout for order %s: %s", order.id, error.code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "payment_failed") from error
    except OSError as error:
        log.error("stripe unreachable: %r", error)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "payment_failed") from error
    url = data.get("url")
    if not url:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "payment_failed")
    return url


def check_signature(payload: bytes, header: str | None) -> None:
    """Stripe signs every callback; without the signature anybody could grant themselves a paid ad."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhook_not_configured")
    parts = dict(
        piece.split("=", 1) for piece in (header or "").split(",") if "=" in piece
    )
    timestamp, given = parts.get("t"), parts.get("v1")
    if not timestamp or not given:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad_signature")
    if abs(time.time() - int(timestamp)) > WEBHOOK_TOLERANCE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "stale_signature")
    expected = hmac.new(
        settings.stripe_webhook_secret.encode(),
        f"{timestamp}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, given):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad_signature")


async def handle_event(session: AsyncSession, event: dict) -> str:
    """Only one kind of event matters: the checkout was completed and the money is there."""
    kind = event.get("type")
    if kind != "checkout.session.completed":
        return "ignored"
    data = (event.get("data") or {}).get("object") or {}
    order_id = (data.get("metadata") or {}).get("order_id") or data.get("client_reference_id")
    if not order_id:
        return "ignored"
    order = await session.get(Order, int(order_id))
    if order is None:
        log.warning("stripe paid an order we do not have: %s", order_id)
        return "unknown"
    await mark_paid(session, order, "card", data.get("payment_intent") or data.get("id"))
    return "applied"
