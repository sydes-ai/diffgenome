from unittest.mock import MagicMock

from shop.order_service import OrderService


def test_place_with_unspecced_mocks() -> None:
    # Negative control: these mocks carry no spec, so nothing *observable* says what they
    # stand in for. diffgenome must report them as unresolved rather than guess.
    pricing = MagicMock()
    pricing.quote.return_value = 700
    inventory = MagicMock()

    order = OrderService(pricing, inventory).place("c-2", ["C"])

    assert order.total_cents == 700
