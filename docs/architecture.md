# Architecture

This covers the smallest architecture that can test the hypothesis in the
[README](../README.md). Anything not needed for [experiment 01](experiment-01.md) is marked
*later* and is not built.

## 1. Critical analysis of the idea

### What stitching does and does not establish

A stitch joins two facts:

- **A:** in test A, `OrderService.place` called a mock standing in for `PricingService.quote`.
- **B:** in test B, the real `PricingService.quote` ran and called `PriceRepository.price_for`.

The join key is the **symbol** `PricingService.quote`. The join is *context-insensitive*.
Test A's call might have used arguments, or object state, that make the real `quote`
behave nothing like it did in test B. So a stitched path means *every segment was really
executed, and the segments line up at a real call site*. It does **not** mean *this whole
path runs in production*. It's an over-approximation, though a much tighter one than a
static call graph, since each segment has runtime evidence behind it.

The seam is also unsound in the other direction. After the mock returns in test A, test A
keeps running on a **fabricated** return value. The part of A *after* the mock is
conditioned on a value that real `quote` may never produce.

What follows:

- The model records the seam explicitly (`EvidenceKind.STITCHED`, with both the call site
  and the fragment). Paths are never flattened.
- When a target has several fragments (e.g. `quote` with items versus with an empty
  cart), all of them are attached as **alternatives**, each with its own provenance.
  Picking one would be a claim we can't back up.
- The tracer records bounded argument summaries at mock call sites and fragment roots, so
  *contract-aware* stitching (discarding fragments whose inputs can't match the call site)
  can be added later without re-tracing.

### Is the hypothesis plausible?

The **mechanism** is plausible, and a quick spike confirmed its key technical parts in
Python 3.12 (§4). What's genuinely open is whether it's **useful on real repositories**.
That depends on three things we can measure but can't know ahead of time:

1. **Resolution rate:** how many mock calls in real test suites can be classified
   deterministically. Python code uses spec-less `MagicMock()` a lot, and that could sink
   the approach.
2. **Fragment availability:** how many internal targets have at least one real execution
   in the existing tests.
3. **Stitch precision:** how many stitched paths correspond to paths that really occur
   end-to-end. This can only be measured on a repo where end-to-end runs *are* possible,
   used as ground truth.

Experiment 01 tests the mechanism. Items 1–3 need the later experiments (§9).

## 2. Pipeline

```
┌─────────────── language-specific ───────────────┐   ┌────────── language-agnostic ─────────┐
 test runner ──► collector (tracer) ──► TestExecution ──► resolver ──► stitcher ──► graph / render
 (pytest)        sys.monitoring          (JSON, one        (rules)      (fragments,   (text tree
                 + unittest.mock facts    per test)                      provenance)   for exp 01)
```

- **Collector** (Python-specific): runs the existing unit tests and emits one
  `TestExecution` per test. It records facts only: calls, and for each mock call, what
  the mock object itself says about its spec. It never classifies anything.
- **Resolver**: turns each mock call's facts into a `MockResolution`
  (internal / external / unresolved) using ordered deterministic rules. It knows the
  repository's source roots and nothing else.
- **Stitcher**: indexes real calls by symbol across executions, then expands mock
  boundaries into fragments, recursively. It produces edges that each carry `Evidence`.
- **Renderer**: prints the stitched tree with →, ⇢ and boundary markers. That's enough
  for experiment 01. A persistent graph store is *later*.

Only the collector knows about Python. A Java/Go/Rust collector would emit the same
`TestExecution` records and reuse everything to its right.

## 3. Data model

Defined in [`src/diffgenome/model.py`](../src/diffgenome/model.py). There are two layers,
and keeping them apart is the main design decision.

### Observation (tracer output: facts)

| Type | Meaning |
|---|---|
| `SymbolId` | `"<lang>:<qualified name>"`, e.g. `py:shop.pricing_service.PricingService.quote`. **The join key for stitching.** Both sides of a seam must name the same function identically. |
| `Symbol` | id, `Origin` (`REPO`, `TEST`, `EXTERNAL`, `UNKNOWN`), source location |
| `TestExecution` | one test run: `test_id`, `kind` (existing test or generated probe), outcome, revision, call tree |
| `CallNode` | one call in one execution: id, parent, callee symbol, optional `MockTarget`, bounded args summary |
| `MockTarget` | facts read off a mock at call time: root `spec`, attribute `path` (`("execute", "()", "fetchone")`), the `member` definition that path names (found through the MRO), and that member's file |

Mock calls are **leaves**: a call into a mock is a call into a stand-in, not into the
system under test.

### Interpretation (derived, always with provenance)

| Type | Meaning |
|---|---|
| `MockResolution` | `MockClass.INTERNAL` / `EXTERNAL` / `UNRESOLVED`, the target `SymbolId`, and the **rule** that decided it |
| `Evidence` | `kind`, `site` (the observed `NodeRef` that grounds it), `rule` (for anything derived from a mock), `fragment` (stitched only) |
| `Edge` | caller → callee + one `Evidence`. The graph is a multiset of these, and one pair of symbols can have many pieces of evidence. |

`EvidenceKind`:

| Kind | Rendered | Meaning |
|---|---|---|
| `OBSERVED` | `→` | real call, real callee, same execution |
| `STITCHED` | `⇢` | call site hit an internal mock; the callee's continuation comes from `fragment` in another execution |
| `INTERNAL_GAP` | `→ [gap]` | internal mock with no real execution of the target anywhere; a probe candidate |
| `EXTERNAL_BOUNDARY` | `→ [external]` | exploration stops here |
| `UNRESOLVED_MOCK` | `→ [unresolved]` | not enough evidence to classify; reported, never guessed |
| `STATIC` | `---→` | *later:* statically possible and never executed |

A precise point about the ⇢ edge: the *call* `OrderService.place → PricingService.quote`
**was** observed in test A, against a mock. The *continuation* was not. So `Evidence.site`
always points at a real observation, even for stitched edges. `fragment` says where the
borrowed continuation came from.

`model.py` enforces the provenance invariants at construction:

- stitched evidence must have a fragment and a rule;
- observed evidence must have neither;
- boundary kinds must have a rule and no fragment.

Generated probes (*later*) produce `TestExecution(kind=GENERATED_PROBE)`, so every edge
derived from one can be traced back to a probe rather than an existing test.

**The genome encoding** (interning `SymbolId`s into integers and storing executions as
compact sequences) is a storage optimisation. It's *later*, and it will always keep the
symbol table.

## 4. Python collector

A pytest plugin that turns tracing on only for the **call phase** of each test.

**Instrumentation:** `sys.monitoring` (PEP 669, Python ≥ 3.12), on its own tool id.

- `PY_START` / `PY_RETURN` / `PY_UNWIND` on in-scope code maintain a per-thread shadow
  stack and build the `CallNode` tree. A code object is in scope when its file is under a
  configured source root (`REPO`) or test root (`TEST`). Out-of-scope code locations
  return `sys.monitoring.DISABLE`, so the stdlib and site-packages cost roughly nothing
  after the first hit.
- The `CALL` event fires *at the call site* and hands us the callable. If the caller is
  in scope and `isinstance(callable, unittest.mock.NonCallableMock)`, we record a mock
  leaf under the current shadow-stack top. That gives exact caller attribution, which a
  plain `settrace` can't: a mock's own frames live in `unittest/mock.py`.
- **Symbol naming:** module path derived from the file's location under its source root,
  plus `code.co_qualname`.

**Mock facts:** walk `_mock_parent` / `_mock_new_parent` up to the root mock to get
the attribute path (`"()"` marks a return value). Read the root's `_spec_class`. Resolve
the path's first attribute statically on the spec class through its MRO
(`inspect.getattr_static`) to find the *defining* function, and use its
`__module__.__qualname__` as `member`.

**Spike result** (Python 3.12, recorded while writing this document): the `CALL` event
reports the mock as the callable, attributed to the calling function.
`create_autospec(PricingService, instance=True).quote` resolves to root spec
`PricingService` with path `["quote"]`. `create_autospec(sqlite3.Connection).execute(...).fetchone()`
resolves to root spec `sqlite3.Connection` with path `["execute", "()", "fetchone"]`.
A spec-less `MagicMock()` has spec `None`.

**Output:** one JSON `TestExecution` per test, written to `.diffgenome/traces/`.

**Known collector limits** (the experiment 01 fixture avoids them on purpose):

- Generators and coroutines (`PY_YIELD`/`PY_RESUME` break a naive shadow stack).
- Threads beyond per-thread stacks.
- Code run *inside* a mock call: `side_effect=` callables and `wraps=` delegation. This
  needs the mock call's extent to be delimited, most likely with a thin wrapper around
  `unittest.mock.CallableMixin._mock_call`.
- Mocks called directly from test code are recorded with a `TEST`-origin caller and never
  used as stitch sites.
- Fixture/setup-phase execution is not traced yet.
- Interaction with coverage.py, which also uses `sys.monitoring`, on another tool id.
- `_spec_class`, `_mock_parent` and friends are private `unittest.mock` attributes. They
  have been stable for years, but diffgenome should pin its Python versions and test
  against them.

## 5. Mock resolution (conservative)

The rules are ordered, and the first one that matches decides. Each `MockResolution`
records which rule fired.

| # | Rule | Condition | Result |
|---|---|---|---|
| R1 | `no-spec` | root mock has no spec | `UNRESOLVED` |
| R2 | `spec-in-tests` | the spec'd object is defined under a test root (a specced fake) | `UNRESOLVED` |
| R3 | `spec-outside-repo` | spec defined outside the source roots, or in C | `EXTERNAL`, whatever the path |
| R4 | `spec-member` | spec in repo and `member` resolved | `INTERNAL`, target = `member` |
| R5 | `internal-return-chain` | spec in repo but the path crosses `"()"` (e.g. `repo.get(x).save()`) | `UNRESOLVED`: we don't know the return value's real type |

The rules deliberately **don't use names**. A spec-less mock called `.quote(...)` is
*not* linked to `PricingService.quote`, even if that's the only `quote` in the repo.
Name-, type-annotation- and injection-site–based inference is a *later*, separate, weaker
rule family. Its results get their own rule names so they can be filtered out.

Later rules, in the order they're likely to be worth adding:

- `patch-target`: record `unittest.mock.patch("pkg.mod.Name")` targets, which name the
  replaced object exactly.
- `sole-implementation`: the spec is an ABC/`Protocol` with exactly one concrete subclass
  in the repo. It's weaker, and labelled as such. With several implementations it's
  ambiguous: report the candidates rather than pick one.
- `injection-annotation`: static analysis of the constructor parameter a spec-less mock
  was passed into.
- `llm-ranked`: an LLM ranks candidates for mocks nothing above can resolve. Its output is
  a *hypothesis* with its own rule name. It's never promoted to fact without
  corroboration (§7).

Adapters, meaning in-repo classes that wrap an external SDK (e.g. `InventoryService`
wrapping HTTP), are **internal**. Exploration continues into them. Their own tests should
mock the SDK, which is where the external boundary really is. If they have no tests,
that's a gap, and a probe candidate.

## 6. Stitching

```
index: for every passing execution E, for every real CallNode n in E:
           fragments[n.symbol] += (E, n)          # a fragment is a call *subtree*, at any depth

expand(E, node, on_path):
    for child in children(E, node):
        if child is a real call:     emit OBSERVED;  expand(E, child, on_path)
        else resolve(child.mock) ->
            EXTERNAL   : emit EXTERNAL_BOUNDARY (leaf)
            UNRESOLVED : emit UNRESOLVED_MOCK   (leaf)
            INTERNAL t :
                if no fragments[t]: emit INTERNAL_GAP (leaf)          # probe candidate
                for (E2, n2) in fragments[t]:
                    if t in on_path: emit STITCHED to a cycle marker; continue
                    emit STITCHED(site=child, fragment=(E2, n2))
                    expand(E2, n2, on_path ∪ {t})
```

- The seed is any execution. Experiment 01 seeds from the controller test.
- Fragments with the same shape are merged for display, and their provenance lists are
  concatenated.
- Recursion is bounded by `on_path` (cycles) and a depth limit.
- Stitched paths are never materialised as flat paths. A fragment-per-seam tree keeps the
  alternatives explicit and avoids path explosion.

## 7. Deterministic vs LLM

| Concern | Who | Why |
|---|---|---|
| Which calls happened, in what order, from where | **deterministic** (tracer) | ground truth; an LLM adds nothing but error |
| Which calls hit mocks; the mock's spec and path | **deterministic** | read directly off the mock objects |
| Internal/external classification when a spec exists | **deterministic** | the spec's definition file versus the repo roots |
| Stitching, provenance, graph, rendering | **deterministic** | pure data transformation |
| Resolving spec-less / ambiguous mocks | *later:* static inference, then **LLM as ranked hypothesis** | tagged with its own rule and never counted as fact |
| Writing generated unit probes | *later:* **LLM-assisted** | construction needs code synthesis. **Validity is checked deterministically:** the probe must pass, must execute the target symbol (checked by tracing it), and must not touch the network or filesystem (enforced by a socket/FS guard) |
| Which gaps to explore first | *later:* heuristic, then LLM | a judgement call |
| Explaining paths to humans | *later:* LLM | presentation only |

## 8. Main risks and open questions

1. **Stitch soundness** (§1). Symbol-level joins over-approximate. Can argument-shape
   contracts at the seam cut false paths without re-running anything?
2. **Spec-less mocks** may dominate real Python suites, which would push most resolution
   into the weak, inferred rule families. This needs measuring early (experiment 02).
3. **`patch()`-style mocking** replaces module attributes and functions, not injected
   objects. It needs the `patch-target` rule to get off the ground.
4. **Hand-written fakes** (`class FakePricing: ...`) aren't `unittest.mock` objects. They
   show up as real calls into `TEST`-origin code. Detecting them as boundaries is an open
   problem.
5. **Polymorphism:** a spec on an interface gives a set of candidate targets, not one.
6. **Symbol identity drift:** the tracer names functions from files, while the resolver
   names them from `__module__.__qualname__`. If the two differ (odd `sys.path`, namespace
   packages, re-exports, decorators that don't `functools.wraps`), stitching fails
   *silently*. Experiment 01 must check that the join works, not assume it.
7. **Granularity:** private helpers and dunder methods add noise. We'll need a
   presentation-level collapse policy. The raw trace keeps everything.
8. **What counts as "the repository"** in monorepos, with vendored or generated code.
9. **Probe drift into integration tests** (*later*): a probe that "passes" by
   under-mocking. The deterministic guard in §7 is required, not optional.
10. **Cross-language claims:** Mockito mocks always carry their class, so resolution is
    easier in Java, but interface-typed mocks make risk 5 the common case.

## 9. Proposed experiment sequence

1. **Experiment 01, mechanism:** on a controlled fixture, trace → resolve → stitch
   reproduces the expected tree with correct provenance. See [experiment-01.md](experiment-01.md).
2. **Experiment 02, measurement on real repos:** run the collector and resolver on 2–3
   open-source Python projects. Report the resolution rate by rule, fragment availability
   for internal targets, the gap count, and failures of the collector itself. This is
   cheap, and it decides whether probes, `patch-target`, or spec-less inference matter
   most. *Proposed before probes because it tells us which problem is real.*
3. **Experiment 03, generated probes:** fill `INTERNAL_GAP`s with disposable probes under
   the deterministic guard, then re-stitch.
4. **Experiment 04, ground truth:** on a repo that *can* run end-to-end, compare stitched
   paths with observed end-to-end traces to measure stitch precision and recall. This is
   what actually confirms or refutes the hypothesis.

## 10. Deliberately not built

Persistent graph storage, genome encoding, commit-to-commit diffing, test selection,
static analysis, LLM integration, non-Python collectors, a web UI, and any plugin or
extension framework.
