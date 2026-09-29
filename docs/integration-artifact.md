# The integration artifact: `diffgenome-change/1`

The contract between DiffGenome and a consumer such as Sydes. It is the *only* thing a
consumer reads: no collector, corpus, graph or composer type crosses this line. It is a
bounded, change-centred projection of the behavioral graph, deterministic for a given graph,
and consumable without the trace corpus. `graph.json` remains the richer artifact for
DiffGenome's own tools (`inspect`, `evaluate`).

## Producing it

```bash
diffgenome change --runtime go --repo <path> --diff <base..head|commit> \
  --test-root api --tests ./api/ --mock-dir db/mock --out <dir>
```

`change` is the `mvp` pipeline with integrator defaults: existing tests only (`--writer none
--probes 0`, no LLM call) unless a budget is given (`--probes N --writer openai`); callers
followed 5 hops up (`--up 5`) so a deep change meets its entry point; probes only for gaps
within 1 hop of a changed symbol (`--probe-max-distance 1`), the rest listed in `notes`. It writes
`<dir>/diffgenome-change.json` and `<dir>/behavioral-map.md` next to the usual outputs. The
Python surface is `diffgenome.api.analyze_change(...)` / `load_change_artifact(path)`. The
runtime adapter's options (`--runtime`, `--test-root`, `--tests`, `--mock-dir`, `--python`,
`--pytest-arg`, `--source-root`) are forwarded by the integrator opaquely; framework and
runtime knowledge stays inside DiffGenome.

When no artifact can be produced, `change`/`mvp` write `diffgenome-status.json`
(`{"format": "diffgenome-status/1", "status": "refused" | "failed", "reason": "..."}`) in the
same directory and exit non-zero: `refused` (exit 3) when the host has no supported OS
sandbox, since target code is never run unconfined; `failed` (exit 2) when the test
command produced no executions. A consumer in another CI job shows that reason instead of
"missing file".

## Contents

| key | meaning |
|---|---|
| `format` | `diffgenome-change/1` |
| `repository` | `root`, `runtime` (`python/pytest`, `node/jest`, `go/test`), `revision` (git rev analyzed, or `checkout`) |
| `change` | `spec` (the diff), `symbols` (changed in-repo symbols, DiffGenome ids), `symbols_never_executed` |
| `neighborhood` | `up`/`down` bounds and symbol count |
| `budget` | writer, probes requested, attempts, `llm_calls`, whether traces were reused |
| `nodes` | `id` (stable: `<lang>:<qualified name>`), `name`, `file`, `line`, `kind` (callable/declaration), `origin` (repo/test/external/unknown), `changed`, `executed_by` (existing executions that ran the real symbol) |
| `edges` | one per production caller→callee: `evidence` (`observed` / `composed`), `distance`, `join` (composed only: `SYMBOL`/`ARG_SHAPE`/`VALUE`/`STATE`), `state` (`matched` / `unavailable` / `not_consulted` / `n/a`), `exit` (`same` / `kind` / `unknown`), `probe_derived`, `executions` (tests: for a composed edge, the seed that exposed the seam and the fragment that continued it), `probes`, `composed_shapes_by_grade`, `same_shape_alternates`, `ambiguous`, `rules` (resolver rules that fired) |
| `boundaries` | where knowledge stops: `kind` = `external` (stays substituted), `unresolved` (stand-in not attributed), `gap` (no execution of the target), `declaration` (no in-repo body), `os`; with rules, distance and executions |
| `executions` | tests and probes contributing to the neighborhood, with `stimulus`, `outcome` (`passed` / `failed` in DiffGenome's isolated run; only passing executions are composition sources) and the test source `file` (location of the first located test-origin call; null when the collector recorded none) |
| `ambiguous_seams` | seams with several accepted continuations or rejected candidates, with rejection reasons counted |
| `rejected_candidates` | (bounded) each rejected join on a neighborhood seam: caller, target, candidate test, reason (`exit conflict: …`, `type conflict: …`, `state conflict: …`) |
| `probes` | objective kind, target, verdict and reasons per attempt |
| `facts` | the case-metrics table: observed/composed edge counts, joins by grade, rejected, gaps, boundaries, tests contributing, `structural_coverage_ratio_NOT_correctness` |
| `invariants` | the reading rules, repeated in every artifact |

## Reading rules

- `observed` was seen in one execution; `composed` was reconstructed across a stand-in seam
  and is never presented as observed. The grade is the evidence class, not a probability.
- STATE is only consulted after VALUE holds; `state: unavailable` means no fact could be
  compared, never that state matched.
- `structural_coverage_ratio_NOT_correctness` counts symbol pairs with evidence.
- A consumer merges these with its own static view without flattening: an observed edge
  corroborates a static hop; a static hop with no runtime edge stays *possible*; a runtime
  edge the static view lacks is kept and marked runtime-only.

Versioning: additive changes keep `/1`; renaming or re-meaning a field bumps the format.
