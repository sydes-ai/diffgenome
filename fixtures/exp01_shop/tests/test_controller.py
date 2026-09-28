from unittest.mock import create_autospec

from shop.controller import OrderController
from shop.inventory_service import InventoryService
from shop.order_service import OrderService
from shop.pricing_service import PricingService


def test_place_order_returns_quoted_total() -> None:
    pricing = create_autospec(PricingService, instance=True)
    pricing.quote.return_value = 2500
    inventory = create_autospec(InventoryService, instance=True)
    controller = OrderController(OrderService(pricing, inventory))

    response = controller.place_order({"customer_id": "c-1", "skus": ["A", "B"]})

    assert response == {"status": "accepted", "total_cents": 2500}
    pricing.quote.assert_called_once_with(["A", "B"])
    inventory.reserve.assert_called_once_with(["A", "B"])
