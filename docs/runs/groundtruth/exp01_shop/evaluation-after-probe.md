# Ground-truth evaluation
entries: shop.controller.OrderController.place_order
ground-truth in-repo edges: 5   claimed: 5   true: 5   false: 0   missing: 0
edge precision: 1.000   edge recall: 1.000

| evidence | claimed | true | precision |
|---|---|---|---|
| composed | 2 | 2 | 1.000 |
| observed | 3 | 3 | 1.000 |

| join strength (composed) | claimed | true | precision |
|---|---|---|---|
| VALUE | 2 | 2 | 1.000 |

probe-derived edges: claimed 1, true 1, precision 1.000

alternate fragments carried on claimed edges: 0

### path-level: shop.controller.OrderController.place_order
ground-truth sequences 2, claimed 3, matched 1, extra 2 (of which outcome-only mismatches 1), missed 1
  extra:  place_order → place → _validate
  extra:  place_order → place → _validate → reserve → quote
  missed: place_order! → place! → _validate!

## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| ARG_SHAPE | 2 | 2 (1.00) | 0 (0.00) | 2 |
| VALUE | 3 | 3 (1.00) | 3 (1.00) | 3 |

