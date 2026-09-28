# diffgenome behavioral impact report

Change: symbol-centred: py:app.main.create_order, py:app.service.create_order, py:app.service.get_stock, py:app.repository.get_stock, py:app.repository.save_order, py:app.main.read_inventory
Changed symbols (6):
  app.main.create_order  executed by 0 test(s)  ← no existing execution
  app.service.create_order  executed by 0 test(s)  ← no existing execution
  app.service.get_stock  executed by 0 test(s)  ← no existing execution
  app.repository.get_stock  executed by 0 test(s)  ← no existing execution
  app.repository.save_order  executed by 0 test(s)  ← no existing execution
  app.main.read_inventory  executed by 0 test(s)  ← no existing execution

## Behavioral neighborhood (before probes)

### Upstream (what reaches the change)
  (nothing observed reaches the changed symbols)

### Downstream (what continues from the change)

### Tests establishing these paths (0)

## Where knowledge stops (before probes)

## Generated probes
- objective: uncovered_symbol app.main.create_order (from app.main.create_order, d0)
  attempt 1: accepted  model=recorded
  learned 4 observed edge(s):
    + py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku → py:app.main.create_order [raised:py:fastapi.exceptions.HTTPException]
    + py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku → py:app.main.create_order [returned]
    + py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku → py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku.<locals>.DummyUnknownSkuError [returned]
    + py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku → py:tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku.<locals>.DummyUnknownSkuError.__init__ [returned]
- objective: uncovered_symbol app.service.create_order (from app.service.create_order, d0)
  attempt 1: accepted  model=recorded
  learned 1 observed edge(s):
    + py:tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists → py:app.service.create_order [returned]
- objective: uncovered_symbol app.service.get_stock (from app.service.get_stock, d0)
  attempt 1: accepted  model=recorded
  learned 1 observed edge(s):
    + py:tests.test_diffgenome_probe_2_1.test_get_stock_calls_repository_and_returns_value → py:app.service.get_stock [returned]
- objective: uncovered_symbol app.repository.get_stock (from app.repository.get_stock, d0)
  attempt 1: accepted  model=recorded
  learned 1 observed edge(s):
    + py:tests.test_diffgenome_probe_3_1.test_get_stock_reads_from_inventory → py:app.repository.get_stock [returned]
- objective: uncovered_symbol app.repository.save_order (from app.repository.save_order, d0)
  attempt 1: accepted  model=recorded
  learned 1 observed edge(s):
    + py:tests.test_diffgenome_probe_4_1.test_probe_save_order_spies_on_order_ctor_and_appends → py:app.repository.save_order [returned]
- objective: uncovered_symbol app.main.read_inventory (from app.main.read_inventory, d0)
  attempt 1: accepted  model=recorded
  learned 1 observed edge(s):
    + py:tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item → py:app.main.read_inventory [returned]

## Before vs after
| metric | before | after |
|---|---|---|
| observed edges | 0 | 6 |
| composed edges | 0 | 5 |
| strong joins (VALUE+) | 0 | 0 |
| weak joins | 0 | 5 |
| internal gaps | 0 | 1 |
| unresolved boundaries | 0 | 1 |
| external boundaries | 0 | 1 |
| os boundaries | 0 | 0 |
| unsound attempts | 0 | 1 |
| probe-derived edges | 0 | 14 |
| symbols | 6 | 14 |
| tests | 0 | 6 |
| reconstructed / provisional denominator | 0/0 = 0.000 | 6/13 = 0.462 |

Denominator is provisional: observed + composed edges + internal gaps + unresolved
stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior
no execution has come near, and external/OS boundaries, which are terminal by design.

## Remaining after probes
### internal_gap (1)
  d1  app.main.create_order → [gap] app.service.create_order  tests=1  rule=claim-member  probe-derived
### unresolved_boundary (1)
  d1  app.repository.get_stock → [unresolved] builtins.dict  tests=1  rule=claim-unknown-origin  probe-derived
### weak joins (5)
  d1  app.main.create_order ⇢ app.service.create_order  tests=2  join=arg_shape  rule=claim-member  probe-derived
  d1  app.main.read_inventory ⇢ app.service.get_stock  tests=2  join=arg_shape  rule=claim-member  probe-derived
  d1  app.service.create_order ⇢ app.repository.save_order  tests=2  join=arg_shape  rule=claim-member  probe-derived
  d1  app.service.create_order ⇢ app.service.get_stock  tests=2  join=arg_shape  rule=claim-member  probe-derived
  d1  app.service.get_stock ⇢ app.repository.get_stock  tests=2  join=arg_shape  rule=claim-member  probe-derived

## Notes
- cold start: no existing executions; every changed symbol is uncovered
- 6 changed symbol(s) have no existing execution at all: app.main.create_order, app.service.create_order, app.service.get_stock, app.repository.get_stock, app.repository.save_order, app.main.read_inventory

## Behavioral map slice around the changed symbols

```
legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  → [unresolved] stand-in not resolved  → [external] outside the repository  → [os] kernel boundary

# app.main.create_order  [origin=repo executed_by=1 outcomes={'returned': 1, 'raised': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  ├⇢ app.service.create_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├⇢ app.repository.save_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └→ [external] pydantic.main.BaseModel.__init__  [external_boundary rule=claim-outside-repo tests=1 probe-derived]
  │  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │     └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │        └→ [unresolved] builtins.dict  [unresolved_boundary rule=claim-unknown-origin tests=1 probe-derived]
  └→ [gap] app.service.create_order  [internal_gap rule=claim-member tests=1 probe-derived]

# app.service.create_order  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  ├⇢ app.repository.save_order  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)
  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)

# app.service.get_stock  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.main.read_inventory ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_2_1.test_get_stock_calls_repository_and_returns_value →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)

# app.repository.get_stock  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.service.get_stock ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.read_inventory ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_2_1.test_get_stock_calls_repository_and_returns_value →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_3_1.test_get_stock_reads_from_inventory →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └→ [unresolved] builtins.dict  [unresolved_boundary rule=claim-unknown-origin tests=1 probe-derived]  (see above)

# app.repository.save_order  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├app.service.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  ├app.main.create_order ⇢  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  └tests.test_diffgenome_probe_0_1.test_probe_create_order_executes_and_handles_unknown_sku →  [observed outcomes=raised:1,returned:1 tests=1 probe-derived]
  │  └tests.test_diffgenome_probe_1_1.test_create_order_invokes_inventory_and_persists →  [observed outcomes=returned:1 tests=1 probe-derived]
  └tests.test_diffgenome_probe_4_1.test_probe_save_order_spies_on_order_ctor_and_appends →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └→ [external] pydantic.main.BaseModel.__init__  [external_boundary rule=claim-outside-repo tests=1 probe-derived]  (see above)

# app.main.read_inventory  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └tests.test_diffgenome_probe_5_1.test_read_inventory_calls_get_stock_and_returns_item →  [observed outcomes=returned:1 tests=1 probe-derived]
## downstream (what continues from it)
  └⇢ app.service.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]
     └⇢ app.repository.get_stock  [composed join=arg_shape rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)
```

The full repo-level graph with every edge's provenance is `graph.json` next to this report (`graph-before.json` is the state before probes). Query it with `python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.
