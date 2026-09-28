(graph rebuilt from --traces with state facts ignored: VALUE-only baseline)

# Ground-truth evaluation
entries: proc.pipeline.Pipeline.execute
ground-truth in-repo edges: 7   claimed: 7   true: 7   false: 0   missing: 0
edge precision: 1.000   edge recall: 1.000

| evidence | claimed | true | precision |
|---|---|---|---|
| composed | 1 | 1 | 1.000 |
| observed | 6 | 6 | 1.000 |

| join strength (composed) | claimed | true | precision |
|---|---|---|---|
| VALUE | 1 | 1 | 1.000 |

alternate fragments carried on claimed edges: 0

### path-level: proc.pipeline.Pipeline.execute
ground-truth sequences 3, claimed 3, matched 3, extra 0 (of which outcome-only mismatches 0), missed 0
path precision 1.000   path recall 1.000


## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| VALUE | 3 | 3 (1.00) | 0 (0.00) | 3 |

## Join matrix (seams on ground-truth paths)
| seam | candidate fragment | SYMBOL | ARG_SHAPE | VALUE | STATE | EXIT | truth | accepted |
|---|---|---|---|---|---|---|---|---|
| execute ⇢ run | test_run_disabled_skips | ✓ | ✓ | ✓ | · | same | ✓ | ✓ |
| execute ⇢ run | test_run_enabled_closed_repository_raises | ✓ | · | · | · | conflict | ✓ | ✗ |
| execute ⇢ run | test_run_enabled_persists | ✓ | ✓ | ✓ | · | same | ✓ | ✓ |
| execute ⇢ run | test_run_enabled_strict_audits | ✓ | ✓ | ✓ | · | same | ✓ | ✓ |

