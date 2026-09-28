from dataclasses import dataclass

from shop.inventory_service import InventoryService
from shop.pricing_service import PricingService


@dataclass(frozen=True)
class Order:
    customer_id: str
    skus: tuple[str, ...]
    total_cents: int


def _validate(skus: list[str]) -> None:
    if len(set(skus)) != len(skus):
        raise ValueError("duplicate sku in order")


class OrderService:
    def __init__(self, pricing: PricingService, inventory: InventoryService) -> None:
        self._pricing = pricing
        self._inventory = inventory

    def place(self, customer_id: str, skus: list[str]) -> Order:
        _validate(skus)
        self._inventory.reserve(skus)
        total = self._pricing.quote(skus)
        return Order(customer_id, tuple(skus), total)
