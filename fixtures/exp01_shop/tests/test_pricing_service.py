import sqlite3
from unittest.mock import create_autospec

from shop.price_repository import PriceRepository
from shop.pricing_service import PricingService


def test_quote_sums_repository_prices() -> None:
    conn = create_autospec(sqlite3.Connection, instance=True)
    conn.execute.return_value.fetchone.side_effect = [(1000,), (1500,)]

    assert PricingService(PriceRepository(conn)).quote(["A", "B"]) == 2500


def test_quote_empty_cart_is_free() -> None:
    conn = create_autospec(sqlite3.Connection, instance=True)

    assert PricingService(PriceRepository(conn)).quote([]) == 0
    conn.execute.assert_not_called()
