(graph rebuilt from --traces with state facts ignored: VALUE-only baseline)

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
| VALUE | 1 | 1 | 1.000 |

alternate fragments carried on claimed edges: 0

### path-level: proc.pipeline.Pipeline.execute
ground-truth sequences 1, claimed 3, matched 1, extra 2 (of which outcome-only mismatches 0), missed 0
path precision 0.333   path recall 1.000
  extra:  execute → run → skip
  extra:  execute → run → validate → audit → save → persist → save

  extra execute → run → skip: admitted at seam execute ⇢ run with join VALUE
  extra execute → run → validate → audit → save → persist → save: admitted at seam execute ⇢ run with join VALUE

## Join lattice: seam-level precision
| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| VALUE | 3 | 1 (0.33) | 1 (0.33) | 3 |

## Join matrix (seams on ground-truth paths)
| seam | candidate fragment | SYMBOL | ARG_SHAPE | VALUE | STATE | EXIT | truth | accepted |
|---|---|---|---|---|---|---|---|---|
| execute ⇢ run | test_run_disabled_skips | ✓ | ✓ | ✓ | · | same | ✗ | ✓ |
| execute ⇢ run | test_run_enabled_closed_repository_raises | ✓ | · | · | · | conflict | ✓ | ✗ |
| execute ⇢ run | test_run_enabled_persists | ✓ | ✓ | ✓ | · | same | ✓ | ✓ |
| execute ⇢ run | test_run_enabled_strict_audits | ✓ | ✓ | ✓ | · | same | ✗ | ✓ |

