"""The price list and Stripe's callback.

The callback is open to the internet on purpose — that is how Stripe reaches us — and is protected by
the signature it carries, not by who is calling.
"""

import json
from typing import Any

from fastapi import APIRouter, Request, status

from app.api.deps import SessionDep
from app.services import payments, pricing

router = APIRouter(tags=["payments"])


@router.get("/services")
async def services() -> dict[str, Any]:
    """What can be bought and for how much; the words live in the site's own dictionary."""
    return {"products": pricing.price_list(), "card_payments": payments.configured()}


@router.post("/payments/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request, session: SessionDep) -> dict[str, str]:
    """Stripe tells us the money arrived. Anything unsigned is refused."""
    payload = await request.body()
    payments.check_signature(payload, request.headers.get("stripe-signature"))
    event = json.loads(payload.decode() or "{}")
    return {"result": await payments.handle_event(session, event)}
