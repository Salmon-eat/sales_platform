"""The price list.

Kept in code on purpose: four lines that the team changes about once a year, and a table nobody can
edit by accident. Amounts are in cents, so nothing here is ever a float.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    key: str
    amount: int  # cents
    days: int
    # what it attaches to: an ad or a firm's page
    target: str


PRODUCTS: dict[str, Product] = {
    # straight back to the top of "newest", where most people look
    "bump": Product("bump", 199, 0, "listing"),
    # a coloured frame in the lists for a week
    "highlight_7": Product("highlight_7", 399, 7, "listing"),
    # the block above the lists, four places
    "top_7": Product("top_7", 799, 7, "listing"),
    # a firm at the top of the directory for a month
    "company_top_30": Product("company_top_30", 1999, 30, "company"),
}

CURRENCY = "EUR"


def get(key: str) -> Product:
    product = PRODUCTS.get(key)
    if product is None:
        raise KeyError(key)
    return product


def price_list() -> list[dict]:
    """What the site shows on the prices page; the words come from the page's own dictionary."""
    return [
        {"key": p.key, "amount": p.amount, "currency": CURRENCY, "days": p.days, "target": p.target}
        for p in PRODUCTS.values()
    ]
