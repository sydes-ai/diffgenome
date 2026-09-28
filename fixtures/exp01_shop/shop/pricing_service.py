from shop.price_repository import PriceRepository


class PricingService:
    def __init__(self, prices: PriceRepository) -> None:
        self._prices = prices

    def quote(self, skus: list[str]) -> int:
        if not skus:
            return 0
        total = 0
        for sku in skus:  # explicit loop: experiment 01 does not handle generator frames
            total += self._prices.price_for(sku)
        return total
