# Ground-truth evaluation
entries: proc.pipeline.Pipeline.execute
ground-truth in-repo edges: 4   claimed: 7   true: 4   false: 3   missing: 0
edge precision: 0.571   edge recall: 1.000

| evidence | claimed | true | precision |
|---|---|---|---|
| composed | 1 | 1 | 1.000 |
| observed | 6 | 3 | 0.500 |

| join strength (composed) | claimed | true | precision |
|---|---|---|---|
| STATE | 1 | 1 | 1.000 |

alternate fragments carried on claimed edges: 0

### path-level: proc.pipeline.Pipeline.execute
ground-truth sequences 1, claimed 1, matched 1, extra 0 (of which outcome-only mismatches 0), missed 0
path precision 1.000   path recall 1.000


## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| STATE | 1 | 1 (1.00) | 1 (1.00) | 1 |

## Join matrix (seams on ground-truth paths)
| seam | candidate fragment | SYMBOL | ARG_SHAPE | VALUE | STATE | EXIT | truth | accepted |
|---|---|---|---|---|---|---|---|---|
| execute ⇢ run | test_run_disabled_skips | ✓ | ✓ | ✓ | ✗ | same | ✗ | ✗ |
| execute ⇢ run | test_run_enabled_closed_repository_raises | ✓ | · | · | · | conflict | ✓ | ✗ |
| execute ⇢ run | test_run_enabled_persists | ✓ | ✓ | ✓ | ✓ | same | ✓ | ✓ |
| execute ⇢ run | test_run_enabled_strict_audits | ✓ | ✓ | ✓ | ✗ | same | ✗ | ✗ |

