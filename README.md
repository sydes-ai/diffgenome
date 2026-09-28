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
| Collectors (Python symbol plane; Linux OS plane), resolver, composer, renderer | next |
| Sandbox | built alongside the OS-plane collector |
| Generated probes, second runtime, ground-truth comparison, Go | later experiments |

## Documents

- [docs/architecture.md](docs/architecture.md): goal and north star, invariants, the two
  planes and the capture ladder, protocol, boundary resolution, composition and the join
  lattice, sandbox, deterministic vs AI, risks, experiment sequence.
- [docs/experiment-01.md](docs/experiment-01.md): the first validation experiment and its
  success and failure criteria.

## Layout

```
src/diffgenome/      the package (language-agnostic core; collectors under it later)
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
