# exp01_shop — fixture target repository

A deliberately small "repository under analysis" for [experiment 01](../../docs/experiment-01.md).
Its unit tests substitute internal dependencies at different layers so that no single test
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

| Test | Real code exercised | Stand-ins |
|---|---|---|
| `test_controller.py::test_place_order_returns_quoted_total` | Controller, OrderService | `PricingService`, `InventoryService` (autospec: claim in repo → internal) |
| `test_pricing_service.py::test_quote_sums_repository_prices` | PricingService, PriceRepository | `sqlite3.Connection` (autospec: claim outside repo → external) |
| `test_pricing_service.py::test_quote_empty_cart_is_free` | PricingService (short-circuit) | `sqlite3.Connection` (never called) |
| `test_order_service.py::test_place_with_unspecced_mocks` | OrderService | claim-less `MagicMock`s → must stay **unresolved** |

The stand-ins here happen to be `unittest.mock` objects because the fixture is Python.
diffgenome's model sees them only as `SubstitutionNode`s with mechanism `MOCK_OBJECT`.

Run its own suite (must pass before tracing means anything):

```bash
cd fixtures/exp01_shop && python -m pytest -q
```
