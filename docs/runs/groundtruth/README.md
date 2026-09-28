# Ground-truth run records (experiment 05)

- `demo-orders-api/`: hidden whole executions (`ground-truth-traces/`, the six TestClient
  tests), the six gpt-5 probes (`probes/`), the probes-only reconstruction (`graph.json`,
  `map.md`, `report.md`) and its grading (`evaluation.md` / `evaluation.json`).
- `exp01_shop/`: the fixture reconstructed from its six unit tests, before and after the
  recorded `InventoryService.reserve` probe, graded against `fixtures/exp01_shop/groundtruth/`.

Reproduce a grading:

```bash
uv run python -m diffgenome evaluate --graph docs/runs/groundtruth/demo-orders-api/graph.json \
  --ground-truth docs/runs/groundtruth/demo-orders-api/ground-truth-traces \
  --entry py:app.main.create_order --entry py:app.main.read_inventory
```
