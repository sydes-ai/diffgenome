from unittest.mock import MagicMock, create_autospec

import pytest
from shop.inventory_service import InventoryService
from shop.order_service import OrderService
from shop.pricing_service import PricingService


def test_place_with_unspecced_mocks() -> None:
    # Negative control: these mocks carry no spec, so nothing *observable* says what they
    # stand in for. diffgenome must report them as unresolved rather than guess.
    pricing = MagicMock()
    pricing.quote.return_value = 700
    inventory = MagicMock()

    order = OrderService(pricing, inventory).place("c-2", ["C"])

    assert order.total_cents == 700


def test_duplicate_skus_rejected() -> None:
    pricing = create_autospec(PricingService, instance=True)
    inventory = create_autospec(InventoryService, instance=True)

    with pytest.raises(ValueError):
        OrderService(pricing, inventory).place("c-3", ["A", "A"])

    inventory.reserve.assert_not_called()
