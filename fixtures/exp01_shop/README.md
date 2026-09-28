# exp01_shop — fixture target repository

A deliberately small "repository under analysis" for [experiment 01](../../docs/experiment-01.md).
Its unit tests mock internal dependencies at different layers so that no single test
observes the full path.

```
OrderController.place_order
  → OrderService.place
      → _validate
      → InventoryService.reserve   (real impl does HTTP; has NO unit test → coverage gap)
      → PricingService.quote
          → PriceRepository.price_for
              → sqlite3.Connection  (external)
```

| Test | Real code exercised | Mocked |
|---|---|---|
| `test_controller.py::test_place_order_returns_quoted_total` | Controller, OrderService | `PricingService`, `InventoryService` (autospec → internal) |
| `test_pricing_service.py::test_quote_sums_repository_prices` | PricingService, PriceRepository | `sqlite3.Connection` (autospec → external) |
| `test_pricing_service.py::test_quote_empty_cart_is_free` | PricingService (short-circuit) | `sqlite3.Connection` (never called) |
| `test_order_service.py::test_place_with_unspecced_mocks` | OrderService | spec-less `MagicMock`s → must stay **unresolved** |

Run its own suite (must pass before tracing means anything):

```bash
cd fixtures/exp01_shop && python -m pytest -q
```
