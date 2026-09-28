# Ground-truth evaluation
entries: app.main.create_order, app.main.read_inventory
ground-truth in-repo edges: 5   claimed: 5   true: 5   false: 0   missing: 0
edge precision: 1.000   edge recall: 1.000

| evidence | claimed | true | precision |
|---|---|---|---|
| composed | 5 | 5 | 1.000 |

| join strength (composed) | claimed | true | precision |
|---|---|---|---|
| ARG_SHAPE | 5 | 5 | 1.000 |

probe-derived edges: claimed 5, true 5, precision 1.000

alternate fragments carried on claimed edges: 0

### path-level: app.main.create_order
ground-truth sequences 1, claimed 2, matched 1, extra 1 (of which outcome-only mismatches 0), missed 0
  extra:  create_order!

### path-level: app.main.read_inventory
ground-truth sequences 2, claimed 1, matched 1, extra 0 (of which outcome-only mismatches 0), missed 1
  missed: read_inventory! → get_stock! → get_stock

## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| ARG_SHAPE | 5 | 5 (1.00) | 5 (1.00) | 5 |

