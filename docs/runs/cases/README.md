# Case studies (experiment 06)

Three real changes, three runtimes. Each directory holds the canonical evidence graph
(`graph.json`, `graph-before.json`), the behavioral projection (`map.md`), the evidence
slice (`map-evidence.md`), the change-centred slice (`slice.json`), the compact metrics
table (`metrics.json`), the ambiguity/rejected-join report (`ambiguity.md`), the run report
and the probe drafts with logs.

| case | target | change |
|---|---|---|
| `python-kokoro-5fb71ea` | Kokoro-FastAPI (Python) | include voice grades on the voice listing endpoint |
| `node-d77fe2a` | express-typescript-boilerplate (TypeScript/Jest) | reject non-positive pet ages |
| `go-simplebank-5b03c1d` | simplebank (Go/gomock/gin), branch `go-s-01-insufficient-balance` | reject transfers exceeding source account balance |

Query any graph: `uv run python -m diffgenome inspect --graph <case>/graph.json --symbol <suffix> [--behavior|--ambiguity]`.
