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

## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| ARG_SHAPE | 5 | 5 (1.00) | 5 (1.00) | 5 |

