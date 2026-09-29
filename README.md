# diffgenome

> Research prototype. The central question is open, and the project is trying to
> falsify its own approach before scaling it.

**diffgenome is a language-neutral runtime behavioral reconstruction system.** Its input
is an executing process plus a stimulus. Its output is a normalized execution graph that
can be composed across isolated runs, where every edge keeps the record of *why* we
believe it exists.

## The problem

Most real repositories can't be run end to end on a laptop. They need databases, internal
services, queues, cloud credentials and staging config. Yet every program, in every
language, eventually becomes the same thing: a process, in memory, executing instructions,
making calls, crossing into the kernel. That process can be observed. What it needs is a
*stimulus*, and most repositories already have one: unit tests.

Each unit test exercises a small slice of the system and substitutes the rest. Observing
one test gives one **execution fragment**. The system-level behavior is the composition
of many fragments, joined where one fragment's boundary is another fragment's entry point:

```
fragment A (test_controller)           fragment B (test_pricing_service)
  OrderController.place_order             PricingService.quote
    → OrderService.place                    → PriceRepository.price_for
      → [stand-in for PricingService]          → [external: sqlite3]
```

```
OrderController.place_order
  → OrderService.place
  ⇢ PricingService.quote                  seam: composed, join=symbol
    → PriceRepository.price_for
    → [external: sqlite3]
```

```
→   observed directly within one execution
⇢   composed across executions, graded by how strongly the seam matched
```

A composed path is never presented as if one end-to-end execution happened. The call
*into* the stand-in was observed. What the real target does next was observed in a
*different* execution. The ⇢ marks that seam, and the edge records both executions.

## Two planes of observation

| Plane | What it sees | Universality |
|---|---|---|
| **OS plane** | syscalls, sockets, files, processes, native symbols | universal: any language, any process |
| **Symbol plane** | the program's logical functions and calls | per runtime, unavoidably: to a CPU an interpreter's program is *data*, not code |

The OS plane gives **physical boundaries** (the process tried to leave) with no language
knowledge at all. The symbol plane gives the call structure and needs the runtime's help
(hooks, exported metadata, probes). Both feed one event protocol, and every node records
which plane and which fidelity (complete trace or sample) it came from.

Stand-ins are one kind of boundary among many. A mock object, a hand-written fake, a DI
binding, a monkey-patched attribute and a stubbed function pointer are all "control left
the observed symbol space". The core model has no notion of a mock, a test framework or a
language.

## Stimulus is not observation

Existing tests, generated isolated probes and direct calls are all ways to *cause*
execution. None of them is how execution is observed. Generated probes are unit probes:
they run real in-repo code with substitutions kept at genuine external boundaries, inside
a sandbox with no network egress, and any attempt to leave becomes boundary evidence.

## Invariants

```
NO full environment dependency
NO language-specific core
NO hidden evidence upgrades
NO external side effects
NO modifying target repos
NO claiming reconstructed = observed
```

Implementation strategy may change substantially as evidence comes in. These don't.

## North star

For a change-centred region of a repository: how much of the relevant in-repo behavioral
graph can be turned from *unknown / statically possible* into *observed / strongly
composable* using only isolated local execution? Target: 85–90% on realistically testable
code, with the remaining 10–15% explicitly marked rather than guessed. The definition and
its caveats are in [docs/architecture.md §1](docs/architecture.md#1-goal-and-non-goals).

## Status

| | |
|---|---|
| Event protocol and evidence model (two planes, join lattice, provenance invariants) | done: `src/diffgenome/model.py` |
| Controlled fixture repository | done: `fixtures/exp01_shop/` |
| Experiment 01: observability floor per plane + first composition | designed: `docs/experiment-01.md` |
| CPython symbol-plane collector (frame-ancestry attribution, patch interposition claims, patch-proof scoping), resolver, composer (SYMBOL/ARG_SHAPE/VALUE joins, outcome and result checks, shape merging), renderers | done; findings logs in `docs/experiment-01.md` and `docs/experiment-02.md` |
| First real target (Kokoro-FastAPI, 318 tests): 42% of stand-ins resolved, 406 composed edges, 11 gaps | measured; see experiment 02 |
| **MVP**: one command from repo + diff to a confined, AI-probed, before/after behavioral impact report | done; see `docs/experiment-03.md` and `docs/runs/kokoro-8307b0e/` |
| Materialized behavioral graph (`graph.json`, `map.md`, `inspect` command) | done |
| **Second runtime**: Node/TypeScript collector behind the runtime seam; core model unchanged | done; see `docs/experiment-04.md` |
| **Ground truth**: edge precision/recall and seam-level join grading against hidden whole executions | done; see `docs/experiment-05.md` |
| **Third runtime (Go)**, behavioral projection (`map.md`), ambiguity report, path-level ground truth, three real-diff case studies | done; see `docs/experiment-06.md` and `docs/runs/cases/` |
| **STATE rung** (bounded, value-free state facts on all three runtimes), exit categories (`returned-error`/`panic`), adversarial ground truth VALUE-only vs STATE, join matrix and path precision/recall with explanations, state-condition probe objective | done; see `docs/experiment-07.md` and `docs/runs/exp07-state/` |
| **Integration surface**: `diffgenome change` / `diffgenome.api`, the `diffgenome-change/1` artifact, consumed by Sydes `verify-change --behavioral-map diffgenome` | done; see `docs/integration-artifact.md` and `docs/integration-sydes.md` |
| Goroutine/coroutine spawn causality, Linux OS-plane collector, larger targets, state-condition probes against a live writer | next |
| Sandbox | built alongside the OS-plane collector |
| Generated probes, second runtime, ground-truth comparison, Go | later experiments |

## The MVP in one command

```bash
uv run python -m diffgenome mvp --repo <target> --python .venv/bin/python --test-root tests \
  --diff <base..head | commit> --writer openai --out out/run
```

`--runtime node --source-root src --test-root test/unit` drives a Node/TypeScript target and
`--runtime go --test-root api --tests ./api/ --mock-dir db/mock` a Go module the same way;
`--rev <git rev>` analyzes a revision without touching the checkout. It traces the target's unit tests under confinement, builds the repo-level behavioral map,
maps the diff to changed symbols, extracts their behavioral neighborhood, picks the most
valuable gaps and weak joins near the change, asks the model for one isolated unit probe
per deficit, executes each probe in a disposable sandboxed workspace (no network, no writes
outside it, no inherited environment), accepts it only on evidence from its own trace, and
reports before vs after with provenance on every edge. The OpenAI key is read from
`OPENAI_API_KEY`, `~/.config/diffgenome/openai_api_key`, or a Keychain item
`diffgenome-openai`; it never reaches the sandbox. `--writer recorded:<dir>` replays saved
probes deterministically. The run leaves `graph.json` (the canonical evidence graph with
provenance), `map.md` (the behavioral projection around the change: production behavior,
tests and probes as evidence), `map-evidence.md`, `slice.json`, `metrics.json`,
`ambiguity.md` and `report.md`; `python -m diffgenome inspect
--graph graph.json --symbol <id>` queries the graph, `python -m diffgenome evaluate` grades
a reconstruction against hidden whole executions (with `--traces`: path precision/recall,
an explanation per extra and missed path, and the join matrix per seam; `--no-state`
rebuilds the same corpus as the VALUE-only baseline). `mvp --no-state` does the same for a
whole run.

## Documents

- [docs/architecture.md](docs/architecture.md): goal and north star, invariants, the two
  planes and the capture ladder, protocol, boundary resolution, composition and the join
  lattice, sandbox, deterministic vs AI, risks, experiment sequence.
- [docs/experiment-01.md](docs/experiment-01.md): the first validation experiment, its
  success and failure criteria, and a dated findings log.
- [docs/experiment-02.md](docs/experiment-02.md): the `VALUE` join, the causality-after-seam
  finding, the first real target (Kokoro-FastAPI).
- [docs/experiment-03.md](docs/experiment-03.md): the MVP on a real change, before/after, and
  what generated probes did and did not recover.
- [docs/experiment-04.md](docs/experiment-04.md): the Node/TypeScript runtime and the
  language-neutrality accounting.
- [docs/experiment-05.md](docs/experiment-05.md): reconstruction accuracy against ground truth
  and the join-lattice test.
- [docs/experiment-06.md](docs/experiment-06.md): three real changes across Python, Node and Go,
  the behavioral projection, ambiguity analysis, path-level ground truth, and the
  language-neutrality accounting after three runtimes.
- [docs/integration-artifact.md](docs/integration-artifact.md): the `diffgenome-change/1`
  contract, the only surface an integrator reads.
- [docs/integration-sydes.md](docs/integration-sydes.md): Sydes consuming DiffGenome on a real
  change, before and after, with the merge policy and the integration-boundary decision.
- [docs/experiment-07.md](docs/experiment-07.md): the STATE rung and the exit model, an
  adversarial ground truth where VALUE must fail, VALUE-only vs STATE on the same corpus,
  the Kokoro and Go replays, and the privacy accounting for state.

## Layout

```
src/diffgenome/      the package: language-agnostic core, runtime adapters under collect/
tools/node-collector the Node/TypeScript collector (instrumenter, runtime, Jest hook)
tools/go-collector   the Go collector (AST instrumenter, dg runtime package)
tests/               diffgenome's own tests
fixtures/            small stand-alone *target* repositories that experiments analyze
docs/                architecture and experiment write-ups
```

Larger targets live outside the repo under `~/sample_repos` and are only ever mounted
read-only.

## Development

Requires Python ≥ 3.12. OS-plane work requires Linux (a VM or container on macOS).

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
```
