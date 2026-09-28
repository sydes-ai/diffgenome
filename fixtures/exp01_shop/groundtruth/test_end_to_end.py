"""Whole-stack execution used only as GROUND TRUTH in experiment 05: never part of the
corpus the composer reconstructs from. Everything in the repository runs for real over an
in-memory sqlite database; the one true external (the inventory HTTP call) is substituted."""

import sqlite3
from unittest.mock import MagicMock, patch

from shop.controller import OrderController
from shop.inventory_service import InventoryService
from shop.order_service import OrderService
from shop.price_repository import PriceRepository
from shop.pricing_service import PricingService


def _stack() -> OrderController:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE prices (sku TEXT PRIMARY KEY, cents INTEGER)")
    conn.executemany("INSERT INTO prices VALUES (?, ?)", [("A", 1000), ("B", 1500)])
    pricing = PricingService(PriceRepository(conn))
    inventory = InventoryService("http://inventory.local")
    return OrderController(OrderService(pricing, inventory))


def test_place_order_end_to_end() -> None:
    response = MagicMock()
    response.status = 201
    context = MagicMock()
    context.__enter__.return_value = response
    with patch("urllib.request.urlopen", return_value=context):
        result = _stack().place_order({"customer_id": "c-1", "skus": ["A", "B"]})
    assert result == {"status": "accepted", "total_cents": 2500}


def test_duplicate_skus_end_to_end() -> None:
    import pytest

    with pytest.raises(ValueError):
        _stack().place_order({"customer_id": "c-3", "skus": ["A", "A"]})
