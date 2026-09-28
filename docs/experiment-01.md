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
silently.

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
| S11 | **Physical boundary evidence.** With `InventoryService` run un-substituted inside the sandbox (a direct-call stimulus, not a test), C1 records `OS_BOUNDARY connect … ENETUNREACH` attributed to `InventoryService.reserve`, and nothing leaves the sandbox. |
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
