"""Money rules that hold without a database: the price list, the clock and the signature."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.order import Order
from app.services import payments, pricing

NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


def test_the_price_list_is_whole_cents_and_known_targets() -> None:
    for product in pricing.PRODUCTS.values():
        assert isinstance(product.amount, int) and product.amount > 0
        assert product.target in ("listing", "company")
    assert pricing.get("bump").days == 0  # a raise is instant, it does not last
    with pytest.raises(KeyError):
        pricing.get("gold_stars")


def test_time_bought_adds_on_instead_of_resetting() -> None:
    # nothing yet: seven days from now
    assert payments._extend(None, 7, NOW) == NOW + timedelta(days=7)
    # still running: the new week starts when the old one ends
    running = NOW + timedelta(days=3)
    assert payments._extend(running, 7, NOW) == running + timedelta(days=7)
    # long finished: from now, not from the old date
    assert payments._extend(NOW - timedelta(days=30), 7, NOW) == NOW + timedelta(days=7)


def test_a_checkout_asks_stripe_for_the_right_amount() -> None:
    order = Order(id=5, product="top_7", amount=799, currency="EUR")
    fields = dict(payments.checkout_fields(order, "Citobazar · top_7", "https://s/ok", "https://s/no"))
    assert fields["line_items[0][price_data][unit_amount]"] == "799"
    assert fields["line_items[0][price_data][currency]"] == "eur"
    assert fields["metadata[order_id]"] == "5"
    assert fields["mode"] == "payment"


def test_an_unsigned_callback_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    with pytest.raises(HTTPException) as refused:
        payments.check_signature(b"{}", None)
    assert refused.value.detail == "bad_signature"


def test_without_a_secret_nothing_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    with pytest.raises(HTTPException) as refused:
        payments.check_signature(b"{}", "t=1,v1=abc")
    assert refused.value.status_code == 503
