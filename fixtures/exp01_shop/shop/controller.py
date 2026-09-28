from typing import Any

from shop.order_service import OrderService


class OrderController:
    def __init__(self, orders: OrderService) -> None:
        self._orders = orders

    def place_order(self, request: dict[str, Any]) -> dict[str, Any]:
        order = self._orders.place(request["customer_id"], list(request["skus"]))
        return {"status": "accepted", "total_cents": order.total_cents}
