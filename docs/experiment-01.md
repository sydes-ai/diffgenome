# Experiment 01: observability floor per plane, and one composed seam

## Questions

**Q1 (capture).** Exercising code only through isolated unit-level stimuli, how much of the
ordered source-level execution can each observation plane recover, and how much
runtime-specific help does the symbol plane need?

**Q2 (composition).** Can independently observed fragments be joined across one internal
boundary while every edge keeps its provenance (observed vs composed vs boundary), and the
negative controls stay unresolved?

Q1 is the measurement this project has been missing. Q2 is the mechanism check that the
rest of the roadmap depends on.

## What this experiment can and cannot show

It **can** produce the per-plane recall numbers, show whether caller attribution survives a
real web framework and a portal thread, show that the join key lines up across executions,
and show that provenance survives composition.

It **cannot** show that composition is *useful* on real code (claim-less stand-ins,
interposition, fakes and missing coverage may dominate: experiment 02), nor that composed
paths are *true* (experiment 05). A pass means "the planes behave as predicted and the
plumbing is sound". It does not mean "the hypothesis holds".

## Targets

Both are analyzed read-only inside the sandbox.

**A. `fixtures/exp01_shop/`** (controlled, in this repo). Constructor-injected stand-ins at
different layers so that no single test observes the full path:

```
OrderController.place_order
  → OrderService.place
      → _validate
      → InventoryService.reserve   real impl does HTTP; NO test          (gap)
      → PricingService.quote
          → PriceRepository.price_for
              → sqlite3.Connection.execute(...).fetchone()             (external)
```

| Test | Role |
|---|---|
| `test_controller.py::test_place_order_returns_quoted_total` | **Seed.** Real controller and `OrderService`; `PricingService`/`InventoryService` are autospecced stand-ins (claim: their classes). |
| `test_pricing_service.py::test_quote_sums_repository_prices` | **Fragment.** Real `PricingService`, `PriceRepository`; `sqlite3.Connection` stand-in (claim outside repo). |
| `test_pricing_service.py::test_quote_empty_cart_is_free` | **Second fragment** for the same target on a different path; tests alternatives and join grading. |
| `test_order_service.py::test_place_with_unspecced_mocks` | **Negative control.** Claim-less stand-ins; must stay unresolved despite `.quote` matching a real method name. |
| `test_order_service.py::test_duplicate_skus_rejected` | **Raising fragment** for `OrderService.place` (added 2026-09-28 after the outcome finding). |
| `test_controller.py::test_place_order_with_order_service_stand_in` | **Second seed** whose stand-in is `OrderService`: three fragments for `place`, one of which raised; exercises outcome conflict and two-hop recursion. |

**B. `~/sample_repos/demo-orders-api`** (real-ish). FastAPI app, 6 tests through
`TestClient`, in-memory repository, **no stand-ins at all**. Real path per request:

```
test → TestClient → [Starlette/anyio portal thread] → app.main.create_order
                                                        → app.service.create_order
                                                            → app.service.get_stock
                                                                → app.repository.get_stock
                                                            → app.repository.save_order
```

This is the capture stress: framework frames and a thread hop between stimulus and code,
and a repo where composition is unnecessary because every test already runs in-process
end to end. It doubles as the ground-truth target for experiment 05.

Simplifications the fixture keeps on purpose (each a known collector limit): synchronous
code, no generators, no `side_effect` callables, constructor injection only.

## Part 1: capture floor (Q1)

Run every test of both targets under each configuration, one at a time, in the Linux
sandbox. Record an `Execution` per test per configuration.

| Cfg | Plane | Fidelity | Collector | Expected on Python |
|---|---|---|---|---|
| C1 | OS | complete | syscall tracing (`strace -f` / ptrace) | boundaries only; **zero** in-repo symbols |
| C2 | OS→symbol | complete | uprobes on `_PyEval_EvalFrameDefault` + frame decoding, or USDT `function__entry` if the interpreter has it | in-repo symbols recoverable only via runtime data structures |
| C3 | symbol | sampled | `perf record` + `PYTHONPERFSUPPORT=1` perf-map | symbols present, ordering absent, most short functions missed |
| C4 | symbol | complete | `sys.monitoring` pytest plugin | full ordered tree; baseline |

C4 is validated by hand on the fixture and then used as ground truth for the recall of
C1–C3. For each configuration and test, compute:

- **symbol recall**: in-repo `SymbolId`s recovered ÷ ground truth;
- **ordered-edge recall**: observed caller→callee edges recovered ÷ ground truth;
- **attribution correctness**: fraction of substitution/OS events attached to the correct
  in-repo caller (not a framework, runtime or test frame);
- **boundary recall** (C1 vs C4): OS events found ÷ OS events expected. On the fixture the
  expected set is empty (everything is substituted); on `demo-orders-api` it's whatever the
  framework does (`TestClient` may open a socketpair; that's a finding to record, not
  filter);
- overhead: wall time relative to an untraced run.

The prediction to falsify: *the OS plane alone recovers the logical structure of a managed
runtime.* We expect C1 symbol recall ≈ 0 and C3 ordered-edge recall low, and the point is
to have the number, per target, in the write-up. If C2 turns out cheap and complete, it
changes which collector we build for other runtimes.

C2 is optional if it costs more than a day: note it as unmeasured rather than skip
silently. More generally Part 1 is bounded: its job is to establish the floor and choose
the capture architecture, not to benchmark tracing tools. Composition and gap discovery
are the research questions; tooling detours stop as soon as the prediction is answered.

## Part 2: composition (Q2)

Built on C4 traces of the fixture, plus C1 traces if Part 1 produced them:

1. `diffgenome.collect.py_monitoring`: pytest plugin emitting `Execution` JSON with
   `CallNode`s and `SubstitutionNode`s (mechanism `MOCK_OBJECT`, claim from spec,
   `identified_by="spec"`).
2. `diffgenome.collect.linux_syscalls`: wraps the test process, emits `OsEventNode`s
   attributed by thread + timestamp to the innermost symbol-plane call.
3. `diffgenome.resolve`: rules R1–R5.
4. `diffgenome.compose`: fragment index + `expand`, `SYMBOL` and `ARG_SHAPE` joins.
5. `diffgenome.render`: deterministic text tree.

No CLI is needed; one integration test drives it.

### Expected rendering (fixture, seeded from the controller test)

```
tests/test_controller.py::test_place_order_returns_quoted_total        [py-sys-monitoring: complete]
├→ shop.order_service.OrderService.__init__
├→ shop.controller.OrderController.__init__
└→ shop.controller.OrderController.place_order
   └→ shop.order_service.OrderService.place
      ├→ shop.order_service._validate
      ├→ [gap] shop.inventory_service.InventoryService.reserve             rule=claim-member
      └⇢ shop.pricing_service.PricingService.quote                         rule=claim-member
         ├ fragment test_pricing_service.py::test_quote_sums_repository_prices   join=arg_shape (list[2]~list[2])
         │  └→ shop.price_repository.PriceRepository.price_for  ×2
         │     ├→ [external] sqlite3.Connection.execute  ×2                 rule=claim-outside-repo
         │     └→ [external] sqlite3.Connection.execute().fetchone  ×2
         └ fragment test_pricing_service.py::test_quote_empty_cart_is_free       join=symbol (list[2]≁list[0])
            (no calls)
```

Negative control, on its own:

```
tests/test_order_service.py::test_place_with_unspecced_mocks
├→ shop.order_service.OrderService.__init__
└→ shop.order_service.OrderService.place
   ├→ shop.order_service._validate
   ├→ [unresolved] stand-in.reserve                                         rule=no-claim
   └→ [unresolved] stand-in.quote                                           rule=no-claim
```

Exact glyphs are settled when the renderer is written; the criteria below are structural.

## Success criteria

Each becomes an assertion in `tests/test_exp01.py` or a table in the write-up.

| # | Criterion |
|---|---|
| S1 | **Unmodified targets.** Both suites pass with and without capture; no target file is edited; the target mount is read-only. |
| S2 | **Numbers exist.** Part 1's recall/attribution/overhead table is produced for C1, C3, C4 on both targets (C2 if attempted), and every `Execution` carries the correct `(plane, fidelity)` on its collectors. |
| S3 | **Attribution across a framework.** On `demo-orders-api`, C4 attributes `app.service.create_order` to `app.main.create_order` as its parent, with framework frames either excluded (out of scope) or present but `EXTERNAL`-origin, never breaking the in-repo chain. Thread hop recorded, not lost. |
| S4 | **Observed chains.** Fixture seed: `place_order → place → _validate`, and two `SubstitutionNode`s whose parent is `OrderService.place`, not a runtime or test frame. Fragment: `quote → price_for` ×2 with external stand-ins under `price_for`. |
| S5 | **Join key.** The resolved target of the seed's `quote` stand-in equals, as a `SymbolId`, the symbol of the real `quote` node in the fragment trace. Asserted, not assumed. |
| S6 | **Classification.** Class-claimed stand-ins → `INTERNAL` via `claim-member`; `sqlite3.Connection` incl. chained `fetchone` → `EXTERNAL` via `claim-outside-repo`; claim-less → `UNRESOLVED` via `no-claim`. |
| S7 | **Composed provenance.** `place ⇢ quote` has kind `COMPOSED`, `site` = the substitution node in the seed, `fragment` = the `quote` node in a pricing test, one edge per fragment (two). The two-item fragment grades `ARG_SHAPE`; the empty-cart fragment grades `SYMBOL` only. |
| S8 | **No laundering.** No edge has `OBSERVED` unless caller and callee are real calls in the same execution with a `COMPLETE` collector. Every edge below a seam cites the fragment's execution. `probe_derived` is `False` everywhere (no probes exist yet). |
| S9 | **Boundaries terminate.** External, unresolved and OS leaves have no children. Nothing is resolved by name. |
| S10 | **Gap reported.** `InventoryService.reserve` is `INTERNAL_GAP` and listed as a probe candidate. |
| S11 | **Physical boundary evidence.** A synthetic canary under diffgenome's control (not target code) attempts a `connect` inside the sandbox as a direct-call stimulus. C1 records `OS_BOUNDARY connect … ENETUNREACH` attributed to the canary's symbol, and nothing leaves the sandbox. Target code is never un-substituted to produce this. |
| S12 | **Determinism.** Two runs give identical `Execution` JSON modulo timestamps and identical rendering. |

## Failure criteria: what would change the plan

- **S3 fails** (attribution breaks across framework/thread): the shadow-stack design is
  insufficient for real code even in Python. Redesign attribution (per-thread stacks keyed
  on runtime thread ids, plus explicit `THREAD` events) before any other runtime.
- **S5 fails** on a clean fixture: symbol identity needs a canonicalization layer before
  anything else. Most important early finding.
- **S6 needs more than R1–R5** here: the conservative resolver is too weak even for
  well-claimed code, and the premise is in doubt.
- **S8 can't hold without special cases**: the observation/interpretation split is wrong;
  redesign the model before experiment 02.
- **S11 fails** because the sandbox can't be made to both block *and* observe: the
  security design and the OS-plane collector need rethinking together; that blocks probes
  (experiment 04).
- **Part 1 shows C2 complete and cheap**: promising, and it changes the collector plan for
  JVM/Node toward runtime-data-structure reading rather than in-runtime hooks.

## Observations to record (not pass/fail)

- The `SYMBOL`-only fragment (empty cart) attached to a two-item call site. Note whether
  `ARG_SHAPE` alone would have ranked it below the compatible fragment, and what `VALUE`
  would have needed.
- Every OS event `demo-orders-api` produces under C1 with nothing but `TestClient`: this is
  the noise floor for physical boundaries in a Python web app.
- Tracer overhead per configuration.
- Anything in the framework frames that made attribution ambiguous.

## Out of scope

Generated probes, interposition (`patch`) resolution, claim-less inference, async and
generators, persistence beyond per-execution JSON, static analysis, LLMs, any runtime
other than CPython.

## Findings log

Running record. Each entry names the prediction it tested, the outcome, and what changed
because of it. Entries are dated; nothing is edited after the fact, only appended.

### 2026-09-28: C4 collector on both targets

Instrument: `diffgenome.collect.py_monitoring` (`sys.monitoring`, complete fidelity) via
the pytest adapter. Both targets read-only, output to a scratch directory, byte-code
writing and pytest's cache disabled. Pinned in `tests/test_collector.py`.

| Prediction | Outcome | Evidence |
|---|---|---|
| **P1** fixture: complete ordered in-repo tree; stand-in calls attributed to the in-repo caller | **holds** | `place_order → place → _validate`, both stand-ins parented on `OrderService.place`; `price_for`'s two stand-ins parented on `price_for`. No test or runtime frame in any tree. (S4) |
| **P2** fixture: claim-derived identity of `quote` equals frame-derived identity | **holds, but not as an independent check** | Both routes reduce to the same function (`symbol_for_code`) whenever the claimed object carries a code object. So equality is a *design consequence*, not an empirical result. The empirical content moved: identity is unified iff a code object exists. Where it doesn't (C members, classes, patch strings, decorators without `wraps`), a second naming scheme applies, and on its first use it produced a wrong identity: `sqlite3.Connection.execute` was named `py:builtins.Connection.execute`. Fixed via `__objclass__`; pinned by a test. **This is the identity-drift risk appearing on run one, on the external side.** |
| **P3** demo-orders-api: in-repo attribution survives Starlette/anyio; the test → endpoint chain is structurally broken by the portal thread | **holds, both halves** | `app.main.create_order → app.service.create_order → {get_stock → repository.get_stock, repository.save_order}` fully attributed, on thread `t1`. The endpoint hangs directly off the stimulus root; nothing links it to the test function, because every frame in between is out of scope and on another thread. (S3: attribution part passes; the thread hop is *recorded*, as `thread=1`, but not *bridged*.) |
| **P4** determinism | **holds** on both targets | `diff -r` of two runs: identical. (S12) |

Unpredicted findings:

1. **Scope is not "under the source root".** The target keeps `.venv` inside its repo, so
   `site-packages` was classified `REPO` and the first trace was 750 KB of pytest
   internals. Rule added: hidden directories and `site-packages`/`node_modules`/
   `dist-packages` are never repository code. This is risk 10 ("what counts as the
   repository") on the first real target; the rule is a patch, not an answer.
2. **A behavior with zero in-repo footprint.** `test_non_positive_quantity_is_rejected`
   produced an empty tree: the 422 is decided entirely by pydantic/FastAPI before any
   in-repo function runs. Real behavior of the system, no in-repo symbol-plane evidence
   at all. Consequence for the north star: "in-repo behavioral structure" must decide how
   framework-owned behavior counts in the denominator, or such tests will look like they
   observed nothing.
3. **Success and failure paths are indistinguishable at the call-tree level.**
   `test_unknown_sku_returns_404` and `test_inventory_lookup_returns_stock` produce the
   same tree shape (`read_inventory → get_stock → repository.get_stock`); one raised
   `UnknownSkuError` inside `get_stock`, the other returned. The protocol records calls,
   not how they ended. A call tree is therefore not a behavioral signature. Candidate
   change (language-neutral): an outcome on `CallNode` (returned / raised `<symbol>`), or
   a separate `EXCEPTION` event. Deferred until the composer needs it, but it bounds what
   "behavioral diffing" can mean over the current protocol.
4. **Instrument fact:** CPython refuses `DISABLE` from `PY_RETURN`/`PY_UNWIND` callbacks
   (only `PY_START`, `CALL` and a few others are locally disableable). Out-of-scope
   returns are ignored instead; cost is bounded by `PY_START` being disabled.
5. **A fake is observed as a substitution with children** (synthetic test, not a target):
   `Service.run ⊗ FAKE FakeRepo.save → _helper`. The mechanism for guardrail item 2 works
   on the symbol plane using only origins (`REPO` caller → `TEST` callee); no mock library
   involvement.

What this changes in the plan:

- S3 is split. *Attribution* across a framework passes. *Bridging* a thread hop from
  stimulus to endpoint is a separate question: the link exists only through out-of-scope
  frames, so either the collector records the spawning relationship between threads
  (universal: thread creation is an OS-plane event) or the stimulus → endpoint edge is
  itself a kind of composition. Decision deferred to the composer; recorded here.
- Part 1's C1 (syscalls) now has a concrete question to answer on `demo-orders-api`: does
  `TestClient` produce any OS events at all, and does the OS plane see the thread creation
  that the symbol plane can only number?
- Finding 3 goes on the protocol change list; finding 2 goes into the north-star
  denominator discussion in architecture §1.

### 2026-09-28: composer, part 2 of the experiment

Instrument: `diffgenome.resolve` (R1–R5), `diffgenome.compose` (fragment index, `expand`,
seam grading), `render_composition`. Pinned in `tests/test_exp01.py` (S5–S10 and P9).

| Prediction | Outcome | Evidence |
|---|---|---|
| **P5** (S6) rules classify every fixture stand-in without names | **holds** | `claim-member`, `claim-outside-repo`, `no-claim`; the negative control composes nothing. |
| **P6** (S7) two `COMPOSED` edges `place ⇢ quote`; two-item fragment `ARG_SHAPE`, empty-cart fragment `SYMBOL` | **half wrong, and the prediction was the wrong half** | Both fragments grade `ARG_SHAPE`. `list[2]` and `list[0]` are the same *type*; size is value-level by the lattice's own definition. My expected rendering had folded size into shape. Kept the definition; the composer notes `size differs (value-level)` on the attempt. **Consequence:** `ARG_SHAPE` cannot separate the two paths of the simplest possible branching function. The `VALUE` join is needed at the first real branch, not later. |
| **P7** (S8–S10) no laundering, boundaries terminate, gap reported | **holds** | `InventoryService.reserve` → `no-fragment` gap; at `min_join=VALUE` both `quote` joins are rejected and listed with notes (the probe queue). |
| **P8** the composer needs something the protocol lacks | **holds** | `args` was a free-form string; seam grading needed structure. Protocol change: `ArgShapes = ((name, shape), ...)`, positional, receiver excluded, `type[size]`. |
| **P9** a returned stand-in is never joined to a raised fragment; the rest compose; recursion continues through them | **holds after two instrument fixes** | The first run *accepted* the raising fragment: my outcome patch had silently not applied. Second run: `unsound … outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError`; the two returning fragments compose at `ARG_SHAPE`; the borrowed `place` fragment expands into the `quote` seam (two hops), every edge citing its own execution. |

Core-model issues exposed, and what was changed:

1. **Outcome compatibility (protocol).** Found on `demo-orders-api` before any stand-in
   was involved: `app.service.get_stock` was indexed four times as a fragment, two of which
   *raised* `UnknownSkuError`, with identical argument shapes to the two that returned.
   Any seed whose stand-in for `get_stock` returned a value would have been joined to a
   raising continuation at `ARG_SHAPE`. The protocol had no call outcome. Added
   `Outcome` (`returned` / `raised:<symbol>` / `unknown`) on `CallNode` and
   `SubstitutionNode`; `grade_seam` returns *unsound* on a returned/raised conflict, and
   `unknown` on either side is noted, never treated as compatible. This is a
   language-neutral fact (every runtime distinguishes normal return from exceptional exit)
   and it closes finding 3 of the previous entry.
2. **Nested-seam provenance.** My S8 assertion ("everything below a seam cites the
   fragment's execution") was wrong for two hops: below a seam, edges cite that fragment
   *until the next seam*. The composer was right; the test was fixed.
3. **First-argument-only stand-in capture weakened `ARG_SHAPE` silently.** For
   `place(customer_id, skus)`, only `customer_id=str` was compared and the discriminating
   `skus` was invisible, so a size difference went unreported. The runtime adapter now
   records all arguments of a stand-in call (it sees them in the call wrapper). The
   general lesson: an `ARG_SHAPE` grade is only as strong as the *coverage* of the
   argument list on both sides; the protocol should probably say how many arguments were
   observable. Not changed yet.
4. **Chained calls on a return value** rendered as a duplicate of the first member. Edge
   callee now carries the path suffix (`sqlite3.Connection.execute.().fetchone`). The
   observed path was always in the node; only the edge label lost it.

Instrument facts: patching `unittest.mock`'s private `_mock_call` gives stand-in outcomes
and full argument lists; assigning a bound method there passes the wrong receiver (found
by the fixture failing under trace, S1 doing its job).

What this changes in the plan:

- `VALUE`-level capture at seams moves up: it is required to select between fragments
  of the first function that branches on an argument. Candidate: bounded, hashed value
  summaries for scalars and sizes for containers at substitution sites and fragment roots.
  This is targeted state capture around seams, not process memory.
- Rejected joins are now first-class output (`attempts`, `gaps`): experiment 04's probe
  generator has its queue.
- `demo-orders-api` composes to pure `OBSERVED`, zero gaps, as a stand-in-free target
  should; it remains the ground-truth candidate for experiment 05.
