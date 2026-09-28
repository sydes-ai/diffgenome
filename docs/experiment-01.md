# Experiment 01: stitching across one internal mock boundary

## Question

Given only independently run unit tests of a small repository, can diffgenome deterministically:

1. trace each test into a call tree that includes its mock calls;
2. classify each mock as internal, external or unresolved, using only facts observable at
   runtime;
3. stitch the internal boundary to a real execution of its target from *another* test;
4. keep observed evidence, stitched evidence and boundaries distinguishable, with full
   provenance, at every edge?

## What this experiment can and cannot show

It **can** show that the mechanism works: tracing mock calls with caller attribution, the
join key lining up across executions, provenance surviving stitching, and the negative
controls holding.

It **cannot** show that the approach is useful on real code. On real code, spec-less
mocks, `patch()`, fakes and missing coverage may dominate. Nor can it show that stitched
paths are *true*. Those questions belong to experiments 02 and 04
([architecture §9](architecture.md#9-proposed-experiment-sequence)). A pass here means
"the plumbing is sound". It does not mean "the hypothesis holds".

## Fixture

[`fixtures/exp01_shop/`](../fixtures/exp01_shop/) is a stand-alone target repository with
its own `pytest.ini`. Real structure:

```
OrderController.place_order
  → OrderService.place
      → _validate
      → InventoryService.reserve   real impl does HTTP; NO unit test        (gap)
      → PricingService.quote
          → PriceRepository.price_for
              → sqlite3.Connection.execute(...).fetchone()               (external)
```

| Test | Role in the experiment |
|---|---|
| `test_controller.py::test_place_order_returns_quoted_total` | **Seed.** Real controller and `OrderService`; `PricingService` and `InventoryService` are `create_autospec` mocks (internal). |
| `test_pricing_service.py::test_quote_sums_repository_prices` | **Fragment.** Real `PricingService` and `PriceRepository`; `sqlite3.Connection` autospec (external). |
| `test_pricing_service.py::test_quote_empty_cart_is_free` | **Second fragment** for the same target, on a different path (short-circuits, calls nothing). Tests how alternatives are handled. |
| `test_order_service.py::test_place_with_unspecced_mocks` | **Negative control.** Spec-less `MagicMock`s. Must stay unresolved, even though `.quote` matches a real method name. |

Deliberate simplifications, each a known collector limit
([architecture §4](architecture.md#4-python-collector)): synchronous code only, no
generators (`quote` uses an explicit loop), no `side_effect` callables, constructor
injection only (no `patch()`).

## What gets built for this experiment

These are the minimum components. Each is a small module, driven by one integration test,
`tests/test_exp01.py`. No CLI is needed yet.

1. `diffgenome.collect.pytest_plugin`: the `sys.monitoring` tracer. Source root
   `fixtures/exp01_shop` (package `shop`), test root `fixtures/exp01_shop/tests`. It runs
   the fixture's suite in a subprocess and writes one JSON `TestExecution` per test.
2. `diffgenome.resolve`: rules R1–R5 from architecture §5.
3. `diffgenome.stitch`: the fragment index and `expand` from architecture §6.
4. `diffgenome.render`: a deterministic text tree.

## Expected output

Seeded from the controller test. Constructors called by the test body are observed facts
and appear in the tree. The generated dataclass `Order.__init__` does not, because its
code object's file is `<string>` and so it's out of scope.

```
tests/test_controller.py::test_place_order_returns_quoted_total
├→ shop.order_service.OrderService.__init__
├→ shop.controller.OrderController.__init__
└→ shop.controller.OrderController.place_order
   └→ shop.order_service.OrderService.place
      ├→ shop.order_service._validate
      ├→ [gap] shop.inventory_service.InventoryService.reserve        rule=spec-member
      └⇢ shop.pricing_service.PricingService.quote                    rule=spec-member  args=(list[2])
         ├ fragment tests/test_pricing_service.py::test_quote_sums_repository_prices   args=(list[2])
         │  └→ shop.price_repository.PriceRepository.price_for  ×2
         │     ├→ [external] sqlite3.Connection.execute  ×2          rule=spec-outside-repo
         │     └→ [external] sqlite3.Connection.execute().fetchone  ×2
         └ fragment tests/test_pricing_service.py::test_quote_empty_cart_is_free       args=(list[0])
            (no calls)
```

The unresolved control, rendered on its own:

```
tests/test_order_service.py::test_place_with_unspecced_mocks
├→ shop.order_service.OrderService.__init__
└→ shop.order_service.OrderService.place
   ├→ shop.order_service._validate
   ├→ [unresolved] mock:?.reserve                                     rule=no-spec
   └→ [unresolved] mock:?.quote                                       rule=no-spec
```

The exact characters of the rendering are settled when the renderer is written. The
success criteria below are about structure, not text.

## Success criteria

All of these must hold. Each becomes an assertion in `tests/test_exp01.py`.

| # | Criterion |
|---|---|
| S1 | **Unmodified target.** The fixture's own suite passes, with and without tracing, and no fixture file is edited to make tracing work. |
| S2 | **Observed chain, seed.** The controller trace contains exactly the real edges `place_order → place → _validate`, and two mock leaves under `OrderService.place` attributed to `OrderService.place` itself, not to a `unittest.mock` frame or to the test. |
| S3 | **Observed chain, fragment.** The pricing trace contains `quote → price_for` (×2) with external mock leaves under `price_for`. |
| S4 | **Join key.** The resolved target of the seed's `quote` mock is equal, as a `SymbolId`, to the symbol of the real `quote` node in the fragment trace. |
| S5 | **Classification.** `PricingService`/`InventoryService` mocks → `INTERNAL` via `spec-member`. `sqlite3.Connection` calls, including the chained `fetchone` → `EXTERNAL` via `spec-outside-repo`. Spec-less mocks → `UNRESOLVED` via `no-spec`. |
| S6 | **Stitch provenance.** The `place ⇢ quote` edge has `EvidenceKind.STITCHED`, `site` = the mock node in the controller test, and `fragment` = the `quote` node in a pricing test. There is one such edge per fragment, so two in total. |
| S7 | **No laundering.** No edge anywhere in the output has `OBSERVED` evidence unless caller and callee are both real calls in the same execution. Every edge below a seam cites the fragment's execution, never the seed's. |
| S8 | **Boundaries terminate.** External and unresolved leaves have no children. Nothing is ever resolved by name. |
| S9 | **Gap reported.** `InventoryService.reserve` shows up as `INTERNAL_GAP`, and the stitcher can list it as a probe candidate. |
| S10 | **Determinism.** Two full runs produce byte-identical JSON traces (modulo timestamps, if any) and identical rendered output. |

Stretch (optional, cheap): add a second hop, e.g. a test that mocks `PriceRepository` in
`PricingService`'s test, plus a `PriceRepository` test, to exercise *recursive* stitching.

## Failure criteria: what would change the plan

- **S2 fails** (mock calls can't be reliably attributed to the calling frame): the
  `sys.monitoring` `CALL` approach is wrong. Fall back to wrapping
  `unittest.mock.CallableMixin._mock_call` and walking frames, then re-evaluate cost.
- **S4 fails** (the join key doesn't line up even on a clean fixture): symbol identity
  needs a canonicalisation layer before anything else. This is the most important finding
  to surface early.
- **S5 needs anything other than R1–R5** on this fixture: the resolver is too weak even
  for well-specced code, and the conservative-resolution premise is in doubt.
- **S7 can't be kept without ad-hoc special cases**: the observation/interpretation split
  in the data model is wrong and must be redesigned before experiment 02.

## Observations to record (not pass/fail)

- The `test_quote_empty_cart_is_free` fragment attaches to a call site whose argument was
  a two-item list. The args summaries make the mismatch visible, but this experiment
  doesn't act on it. Write down whether a simple shape-based contract check would have
  pruned it. That's the seed for contract-aware stitching.
- Tracer overhead on the fixture: wall time with and without tracing.

## Out of scope

Generated probes, `patch()` resolution, spec-less inference, async/generators, persistence
beyond per-test JSON, static analysis, LLMs.
