# diffgenome

> Research prototype. Nothing here is production-ready, and the central question is still open.

**Hypothesis.** We can reconstruct system-level behavioral paths *compositionally* from
isolated unit-test executions. We do this by resolving and traversing the mock boundaries
between in-repo components, with no need for the full application, a staging environment,
databases, queues, or downstream services.

## The problem

Most real repositories can't be run end-to-end on a laptop. They need databases, internal
services, Kafka, cloud credentials and staging config. Most of them *do* have unit tests,
and unit tests run anywhere.

Each unit test sees a small slice of the system. Tracing stops at the first mock:

```
test_controller                       test_pricing_service
  Controller                            PricingService
    → OrderService                        → PriceRepository
      → MockPricingService    (stop)        → Mock(sqlite3.Connection)   (stop)
```

`MockPricingService` isn't the edge of the system. `PricingService` lives in the same
repository, and another test executes it for real. diffgenome resolves that mock to its
real in-repo target, finds executions of the target, and joins the fragments:

```
Controller
  → OrderService
  ⇢ PricingService
  → PriceRepository
  → [external: sqlite3.Connection]
```

```
→   observed directly within one unit-test execution
⇢   joined across unit-test executions (stitched)
```

**A stitched path is never presented as if it had been observed end-to-end.** The call
*into* the mock was observed. What `PricingService` does next was observed in a
*different* execution, possibly with different inputs. The ⇢ marks that seam, and every
edge keeps a record of which executions support it.

## Internal vs external mocks

| Mock stands in for | Examples | diffgenome treats it as |
|---|---|---|
| **Internal**: code whose real implementation is in this repo | `create_autospec(PricingService)` | a **continuation point**: find executions of the real target, stitch, recurse |
| **External**: something outside the repo | Stripe, Kafka, S3, `sqlite3`, HTTP APIs | a **terminal boundary**: record it and stop, never contact it |
| **Unresolved**: not enough evidence to tell | `MagicMock()` with no spec | a **terminal, reported gap**: never guessed |

An internal target that no test executes is a **coverage gap**. A later experiment will
fill gaps with *generated unit probes*: disposable tests that run one component with its
dependencies still mocked. Probes stay unit tests. They never become integration tests and
never reach real external services.

## Principles

1. Observed evidence is ground truth.
2. Stitched evidence stays distinguishable from observed execution.
3. External boundaries end local exploration.
4. Internal mocks are continuation points, not endpoints.
5. Generated tests are isolated unit probes, not integration tests.
6. Staging or full-system execution is never required.
7. An LLM is never responsible for facts that runtime instrumentation can determine.
8. AI can later help with ambiguous mock resolution, probe generation, exploration
   priority and explanation. It does not do basic tracing.
9. Everything above the tracer is language-agnostic and replaceable.
10. The first goal is to prove the hypothesis, not to build a platform.

## Why "genome"

Each execution becomes a normalized sequence of semantic events (symbols and calls), not
raw memory. Across many tests these sequences form a reusable behavioral graph of the
codebase. Later they may be interned into compact ID sequences, but they always map back
to source symbols. Possible uses later on: change-impact analysis, test selection,
behavioral diffing between commits, novel-path detection, and coverage-gap discovery.
None of those are in scope yet.

## Status

| | |
|---|---|
| Core data model (observation vs interpretation, provenance invariants) | done: `src/diffgenome/model.py` |
| Experiment 01 fixture repository | done: `fixtures/exp01_shop/` |
| Python tracer (pytest plugin on `sys.monitoring`) | next |
| Mock resolver, stitcher, text renderer | next |
| Generated unit probes | later experiment |
| Static-analysis evidence | later |

## Documents

- [docs/architecture.md](docs/architecture.md): data model, tracer design, mock
  resolution, stitching, what is deterministic and what may need an LLM, and risks.
- [docs/experiment-01.md](docs/experiment-01.md): the first validation experiment with its
  success and failure criteria.

## Layout

```
src/diffgenome/      the package (language-agnostic core + Python collector)
tests/               diffgenome's own tests
fixtures/            small stand-alone *target* repositories that experiments analyze
docs/                architecture and experiment write-ups
```

## Development

Requires Python ≥ 3.12, because the tracer uses `sys.monitoring` (PEP 669).

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
```
