# Experiment 05: ground-truth reconstruction accuracy

## Question

When diffgenome reconstructs behavior compositionally from isolated execution fragments,
how accurately does that reconstruction match an execution we can observe whole? And do
stronger join grades correspond to more reliable compositions?

## Method

Two cases. In both, the whole executions are captured with the same complete Python
collector, then **hidden**: the reconstruction is built from a corpus that does not contain
them, and graded against them afterwards by `diffgenome evaluate`.

- **Edge precision**: of the in-repo caller→callee edges the reconstruction claims
  (observed or composed) in the downstream neighborhood of the entry symbols, how many
  occur in the ground-truth execution. **Edge recall**: of the ground-truth in-repo edges,
  how many were claimed. Broken down by evidence kind, best join grade, and probe origin.
- **Seam-level lattice test**: for every accepted join whose target lies on a ground-truth
  path, the borrowed fragment's continuation (its observed callees plus the targets of its
  own composed seams) is compared with what the whole execution did from that target:
  *consistent* = no edge the whole execution did not take; *matching* = exactly the whole
  execution's continuation; *outcome ok* = the fragment's outcome kind is one the whole
  execution produced there.
- Missing edges are classified by what the reconstruction had in their place: an internal
  gap, an unresolved stand-in, or nothing at all.

Provenance says why an edge was claimed; this measures whether the claim was right.

### Case A: `demo-orders-api`, cold start from generated probes only

The repository's six tests are `TestClient` end-to-end executions: they *are* the ground
truth (5 in-repo edges under `main.create_order` and `main.read_inventory`, with the
`UnknownSkuError` raising path). The diffgenome setting was simulated from nothing: an
empty corpus, six changed symbols (the whole path) as seeds, and the new cold-start
objective kind (`uncovered_symbol`: a changed symbol with no execution) asking for one
isolated probe per symbol with in-repo collaborators substituted by `autospec` stand-ins.
gpt-5 wrote six probes; all six were accepted on the first attempt (6 model calls).

**The first evaluation exposed a collector defect, not a composition defect.** The
probes-only map had no composed edges at all: `patch(target, autospec=True)` on a
*function* installs a plain function wrapper (with a `.mock` attribute), not a
`NonCallableMock`, so the seams were invisible to the tracer and the probes had been
accepted on their observed test→target edges alone. Fixed in the Python collector and
pinned by a test; the six saved drafts were replayed deterministically (no further model
calls).

| probes-only reconstruction vs hidden whole executions | |
|---|---|
| ground-truth in-repo edges | 5 |
| claimed | 5, all `COMPOSED`, all probe-derived |
| edge precision / recall | **1.000 / 1.000** |
| by join grade | `ARG_SHAPE` 5/5 true (no `VALUE`: the probes' pydantic arguments have no digest and their SKU literals differ from the tests') |
| seam-level | `ARG_SHAPE` 5 seams: 5 consistent, 5 matching, 5 outcome ok |
| false composed continuations | 0 |
| missing continuations | 0 |
| outcome conflicts | 0 |

Reconstructed map (`docs/runs/groundtruth/demo-orders-api/map.md`):
`main.create_order ⇢ service.create_order ⇢ {repository.save_order, service.get_stock ⇢
repository.get_stock}` and `main.read_inventory ⇢ service.get_stock ⇢
repository.get_stock`, every seam a probe-created stand-in composed to a probe-created
fragment. One honest extra: `main.create_order → [gap] service.create_order`, because the
probe also drove the raising path and no returning fragment is outcome-compatible with a
raised stand-in, which is the outcome rule doing its job.

### Case B: `exp01_shop` fixture, existing isolated fragments

Ground truth: two whole-stack executions over an in-memory sqlite database with the one
true external (`urlopen`) substituted, kept in `fixtures/exp01_shop/groundtruth/` outside
the collected test paths so they can never enter the corpus. Reconstruction: the six
existing unit tests, then plus the recorded `InventoryService.reserve` probe. Entry:
`OrderController.place_order`.

| | 6 unit tests | + 1 probe |
|---|---|---|
| ground-truth edges | 5 | 5 |
| claimed / true / false | 4 / 4 / 0 | 5 / 5 / 0 |
| edge precision / recall | 1.000 / **0.800** | 1.000 / **1.000** |
| missing, explained | `place → reserve` shown as `[gap]` | none |
| probe-derived edges | – | 1 claimed, 1 true |

Seam-level lattice test (after the probe; before differs only by one `VALUE` seam):

| join grade | seams | consistent | matching | outcome ok |
|---|---|---|---|---|
| `ARG_SHAPE` | 2 | 2 (1.00) | **0 (0.00)** | 2 |
| `VALUE` | 3 | 3 (1.00) | **3 (1.00)** | 3 |

The two `ARG_SHAPE` seams are the empty-cart `quote` fragment (same argument *type*,
different value, a different branch: consistent because it claims no false edge, not
matching because the whole execution went through `price_for`) and the claim-less-mock
`place` fragment (`"c-2", ["C"]`). The three `VALUE` seams are exactly the whole
execution's continuations.

## Findings

1. **Measured accuracy is perfect on these two cases, and that is a statement about their
   size, not about the method.** 5 ground-truth edges each, no dynamic dispatch, no
   polymorphic seams, no fragments that would produce *wrong* edges rather than fewer
   edges. The composer's over-approximation appeared as `ARG_SHAPE` seams that were
   consistent-but-not-matching, never as false positives. A target where an alternative
   fragment takes a *different* real path would produce false composed continuations;
   neither case had one.
2. **The lattice ordering held where it could be tested.** `VALUE` seams matched the whole
   execution 3/3; `ARG_SHAPE` seams 0/2 matched though 2/2 were consistent. On
   `demo-orders-api` all seams were `ARG_SHAPE` and all matched, because the path has no
   value-dependent branch. `STATE` seams do not exist yet. Result: stronger grades were
   more reliable in the one case with a value-dependent branch; n is tiny.
3. **Generated probes recovered missing true edges with zero false ones**: recall
   0.8 → 1.0 (fixture, 1 probe, 1 edge) and 0 → 1.0 (demo, 6 probes, 5 edges), precision
   1.0 throughout, all probe-derived edges true.
4. **Ground truth found a collector blind spot that no amount of provenance could have.**
   Function-autospec stand-ins were invisible; the probes were "accepted" against a map
   that could never compose. Verification against the map is necessary but not sufficient;
   verification against a whole execution is what caught it.
5. **Composed graphs, not per-seed trees.** The demo map is one graph where five probes'
   fragments are joined at five seams, each edge citing its stand-in site and its fragment;
   `inspect` renders it from `graph.json` without the corpus.

6. **The provisional reconstruction ratio is not a proxy for accuracy.** The same
   demo-orders-api reconstruction that ground truth scores 1.000 / 1.000 reports a
   provisional ratio of 6/13 = 0.462, because every probe's own stand-in enters the
   denominator and `ARG_SHAPE` joins are not counted as strong. The ratio measures how
   much of the *known seam structure* is strongly supported; only ground truth measures
   whether the claims are right. They should never be quoted interchangeably.

## AI efficiency across the pass

| target | model calls | accepted probes | rejected | verified new edges | gaps closed / seams strengthened |
|---|---|---|---|---|---|
| Kokoro-FastAPI (exp 03) | 9 | 3 | 6 (all six from one harness bug: no `PYTHONPATH` in the sandbox) | 16 | 1 closed, 2 weak→`VALUE` |
| express-typescript-boilerplate (exp 04) | 8 | 1 | 7 (2 harness, 2 context, 3 model) | 4 | 1 closed |
| demo-orders-api (exp 05) | 6 | 6 | 0 | 5 composed + 9 observed | 5 seams created and composed |

23 calls, 10 accepted probes, 0 accepted probes later found false against ground truth
(where ground truth exists). Every rejection was decided by execution evidence, never by
the model's claim.

## What this does not show

Two small targets; no false composed continuation was produced to be caught; no `STATE`
seams; no polymorphic or dynamically dispatched seam; no measurement on Kokoro (no whole
execution exists there, which is the premise). The evaluator counts edges, not paths: a
reconstruction with the right edges in the wrong order would score perfectly.
