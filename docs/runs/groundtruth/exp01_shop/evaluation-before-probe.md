# Ground-truth evaluation
entries: shop.controller.OrderController.place_order
ground-truth in-repo edges: 5   claimed: 4   true: 4   false: 0   missing: 1
edge precision: 1.000   edge recall: 0.800

| evidence | claimed | true | precision |
|---|---|---|---|
| composed | 1 | 1 | 1.000 |
| observed | 3 | 3 | 1.000 |

| join strength (composed) | claimed | true | precision |
|---|---|---|---|
| VALUE | 1 | 1 | 1.000 |

missing continuations (ground truth not claimed):
  [gap] shop.order_service.OrderService.place → shop.inventory_service.InventoryService.reserve

alternate fragments carried on claimed edges: 0

### path-level: shop.controller.OrderController.place_order
ground-truth sequences 2, claimed 3, matched 0, extra 3 (of which outcome-only mismatches 1), missed 2
  extra:  place_order → place → _validate
  extra:  place_order → place → _validate → quote
  extra:  place_order → place → _validate → quote → price_for → price_for
  missed: place_order! → place! → _validate!
  missed: place_order → place → _validate → reserve → quote → price_for → price_for

## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| ARG_SHAPE | 2 | 2 (1.00) | 0 (0.00) | 2 |
| VALUE | 2 | 2 (1.00) | 1 (0.50) | 2 |

