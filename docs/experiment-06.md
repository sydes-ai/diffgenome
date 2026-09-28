# Experiment 06: three real changes, three runtimes, ambiguity, ground truth

## What this pass asked

1. Does the behavioral map stay useful on real, multi-symbol diffs?
2. Does composition remain sound when several legitimate continuations exist?
3. Does the language-neutral core survive a third, substantially different runtime (Go)?
4. Can the map be presented as a behavioral view rather than an evidence dump?

Artifacts per case live under `docs/runs/cases/<case>/`: `graph.json` (canonical evidence
graph), `map.md` (behavioral projection), `map-evidence.md` (evidence slice), `slice.json`
(change-centred JSON), `metrics.json` (the compact table), `ambiguity.md` (all ambiguous and
rejected compositions), `report.md`, and the probe drafts with their logs.

## The projection (Part 1, Part 8)

`graph.json` is unchanged and canonical. `map.md` is derived from it: one behavioral edge per
production caller→callee pair with observed and composed evidence merged; tests and probes
appear as evidence lines (`evidence: observed 3 exec · composed VALUE x1 · tests 2 · probes 1`)
and as "reached by" annotations on entrypoints, never as branches; boundaries are leaves
(`[external]`, `[unresolved]`, `[gap]`, `[os]`); seams with more than one materially
different continuation carry `AMBIGUOUS`. A stand-in that claims a *declaration* (a class
with no in-repo constructor body) is labelled `[declaration]` and excluded from gap counts;
the collector marks such symbols with a new universal `Symbol.kind = "declaration"`, so the
rule is not Python-specific. A changed class in a diff is shown as a changed declaration,
not as "never executed".

## Case A: Python, Kokoro-FastAPI `5fb71ea` "include voice grades on the voice listing endpoint"

Changed: `list_voices` (endpoint), `load_voice_grades` (new), `load_openai_mappings`,
`_load_core_json` (4 in-repo seeds). 318 tests traced.

The new static rule mattered here: **60** `factory().member` stand-ins that were
`claim-return-chain` unresolved in every earlier Kokoro run are now resolved through
declared return types (`get_tts_service() -> TTSService`, `get_manager() -> ModelManager`
…), with rule `static-return-type` on every edge they produce. The changed endpoint now maps
end to end:

```
list_voices  [changed; reached by tests test_list_voices, test_list_voices_grades]
  ⇢ get_tts_service (VALUE)                          composed VALUE x6 · +9 same-shape · AMBIGUOUS
     ⇢ TTSService.create (VALUE)                     composed VALUE x3 · +24 same-shape · AMBIGUOUS
        → model_manager.get_manager                   observed 6 · composed SYMBOL x38 · AMBIGUOUS
        → voice_manager.get_manager                   observed 6 · composed VALUE x38 · AMBIGUOUS
        → TTSService.__init__                         observed 25
  ⇢ TTSService.list_voices (VALUE)                   composed VALUE x3 · rule=static-return-type
     → [gap] VoiceManager.list_voices                rule=static-return-type
```

`load_voice_grades` had no execution at all (the change's new function); the cold-start
objective produced a probe that was accepted on the first attempt and added 18 observed
edges. The remaining objectives were rejected on evidence: two probes for the
`VoiceManager.list_voices` gap failed their own assertions; two for the weak
`create ⇢ get_manager` seam executed the target but changed nothing in the neighborhood.

| metric | value |
|---|---|
| changed symbols / behavioral symbols in neighborhood | 4 / 14 |
| observed / composed edges (projected) | 9 / 3 |
| joins SYMBOL / ARG_SHAPE / VALUE / STATE | 0 / 0 / 3 / 0 |
| rejected joins in neighborhood / ambiguous seams | 0 / 5 |
| internal gaps / declarations / unresolved / external | 1 / 0 / 0 / 1 |
| existing tests contributing / probe-derived edges | 30 / 4 |
| LLM calls / accepted / rejected | 5 / 1 / 4 |
| before → after (strong, weak, gaps, observed, composed) | 4,1,1,10,5 → 5,1,1,15,6 |
| structural coverage (not correctness) | 0.909 |
| ground truth | infeasible: the real path needs the Kokoro model files and eSpeak |

## Case B: Node/TypeScript, express-typescript-boilerplate `d77fe2a` "reject non-positive pet ages"

The only real change in this repository's history (its other commits are CI and dependency
bumps). Smallest of the three, but it has the error-vs-success branch the pass asked for.
13 tests traced. Changed: `PetService.create`, `InvalidPetAgeError` (+ constructor).

```
PetService.create  [changed; outcomes returned:1 raised:1; reached by tests 2]
  → InvalidPetAgeError.constructor        observed 1 · tests 1        (the new branch)
  → Pet.toString                          observed 2 · tests 2
  ⇢ Logger.info (ARG_SHAPE)               composed ARG_SHAPE x2 · tests 2 · probes 1
     → Logger.log → Logger.formatScope    probe-derived
     → [unresolved] jest.fn               the probe's own winston mock
  → [unresolved] EventDispatcherMock.dispatch   base type is external (event-dispatch)
  → [unresolved] RepositoryMock.save            base type is external (TypeORM)
```

| metric | value |
|---|---|
| changed / behavioral symbols | 3 / 6 |
| observed / composed edges | 4 / 1 |
| joins | ARG_SHAPE 1 |
| rejected / ambiguous | 0 / 0 |
| gaps / declarations / unresolved / external | 0 / 0 (the changed class is shown as a declaration) / 3 / 0 |
| tests contributing / probe-derived edges | 2 / 4 |
| LLM calls / accepted / rejected (over the whole Node effort) | 8 / 1 / 7 |
| before → after | 0,0,1,7,0 → 0,1,0,9,1 |
| ground truth | infeasible: the real continuation of the fakes is TypeORM against a database |

## Case C: Go, simplebank `5b03c1d` "reject transfers exceeding source account balance"

The Sydes case. Analyzed at branch `go-s-01-insufficient-balance` via `git archive` (the
checkout stays untouched and on another branch). Changed: `Server.createTransfer`,
`Server.checkSufficientBalance` (new). 50 subtests of the `api` package traced (Postgres-
backed `db/sqlc` tests are not run: that is the external boundary).

```
createTransfer  [changed; reached by 11 TestTransferAPI subtests]
  ↑ authMiddleware.<anon>@21  [entrypoint]  reached by 32 tests
  → <anon>@8 (currency validator) → util.IsSupportedCurrency
  → checkSufficientBalance  [changed; 3 tests]  → errorResponse    (the new branch)
  → validAccount → errorResponse
              → [gap] db/sqlc.Queries.GetAccount     rule=claim-member (from the MockGen header)
  → [gap] db/sqlc.SQLStore.TransferTx                 rule=claim-member
```

The gomock stand-ins are claimed deterministically: the generated file states
`Source: …/db/sqlc (interfaces: Store)`, and the package's method sets give a single in-repo
definer per method (`Queries.GetAccount`, `SQLStore.TransferTx`). Both continuations are
sqlc-generated database code, so they are gaps whose real execution needs Postgres.

| metric | value |
|---|---|
| changed / behavioral symbols | 2 / 9 |
| observed / composed edges | 8 / 0 |
| joins | none (no existing test executes a claimed target) |
| rejected / ambiguous | 0 / 0 |
| gaps / unresolved / external (before probes) | 2 / 0 / 0 |
| tests contributing | 14 |
| LLM calls / accepted / rejected | 8 / 2 / 6 (see the Go probe note below) |
| before → after (strong, weak, gaps, observed, composed) | 0,0,2,45,0 → 0,2,2,46,2 |
| structural coverage (not correctness) | 0.885 |
| ground truth | infeasible without Postgres (`db/sqlc` tests) |

Go probe note: the first round's four attempts all failed, two because the harness did not
instrument a probe file added after preparation (no `dg.Begin`, hence no execution although
`go test` passed) and two because the model imported a module absent from the offline cache.
Both were fixed (idempotent instrumenter run before a probe; the conventions now list the
importable modules and the `DBTX` fake pattern). The four drafts were replayed
deterministically after the fixes. Result: **2 accepted** (`Queries.GetAccount` driven by a
hand-written fake `DBTX`/`pgx.Row`, returning; `SQLStore.TransferTx` driven with a fake
`DBTX`, panicking in `execTx`), 1 compile error (an incomplete `pgx.Rows` fake), 1 rejected
on evidence.

```
createTransfer
  → validAccount
     ⇢ db/sqlc.Queries.GetAccount (ARG_SHAPE)     composed ARG_SHAPE x11 · tests 9 · probes 1
        → [unresolved] api.fakeDB.QueryRow         the probe's fake DBTX: the true external boundary
        → [unresolved] api.fakeRow.Scan
  ⇢ db/sqlc.SQLStore.TransferTx (ARG_SHAPE)        composed ARG_SHAPE x1 · tests 2 · probes 1
     → db/sqlc.SQLStore.execTx                     probe-derived, panicked
```

Two things this exposed, both fixed in runtime-neutral code: (1) the acceptance rule
counted gaps closed, strong joins and observed edges but not a *new composed continuation*,
so a probe that created a weak-but-real seam was rejected as "no evidence"; (2) my
type-conflict rule compared dynamic types, so `*gin.Context` at the seam against
`context.backgroundCtx` in the probe (both satisfying the declared `context.Context`) was
condemned like Kokoro's `None` vs `dict`. Structural kinds (None/nil, primitives,
containers) are now decisive; differing object types are "unverified" and cap the seam at
`ARG_SHAPE`. One thing not fixed, recorded: outcome compatibility is by *kind*
(returned/raised), so the `TransferTx` seam joined a stand-in that returned an error to a
fragment that panicked; Go distinguishes those and the protocol's outcome string could
too (`raised:go:*errors.errorString` vs `raised:go:panic:…`), but the composer does not
yet compare beyond the kind.

Final Go metrics: observed / composed (projected) 8 / 2, joins ARG_SHAPE 2, gaps 0 in the
projection (both seams now have continuations), probe-derived edges 5, LLM calls 8 over
two rounds (4 harness-caused failures, 1 model compile error, 1 panic-on-evidence
rejection that later composed, 2 accepted).

## Ambiguity and rejected joins (Part 4)

Across the Kokoro graph (the only one with existing-test fragments for claimed targets):

```
join attempts by grade:   VALUE 415   SYMBOL 152   ARG_SHAPE 137   unsound (rejected) 88
seams with >1 accepted shape or rejected candidates: 109
```

The richest seam: `create_captioned_speech ⇢ process_and_validate_voices`, three accepted
continuation shapes (+31 same-shape), 34 accepted at `ARG_SHAPE` (the stand-in's second
argument is a mock, so its type is unverified), and rejected candidates of two kinds:

```
REJECTED unsound  test_alias_rate_expands_to_a_baserate_tag      type conflict: NoneType≠dict[2]
REJECTED unsound  test_alias_names_are_matched_regardless_of_case type conflict: NoneType≠dict[2]
REJECTED unsound  test_combine_voices_unknown_voice               outcome conflict: stand-in returned, fragment raised ValueError
REJECTED unsound  test_dialogue_endpoint_rejects_unknown_voice    outcome conflict: stand-in returned, fragment raised ValueError
```

Before this pass the type-conflict candidates were **accepted at `SYMBOL` grade**: the
composer treated a known argument-type conflict (`voice_tags=None` at the seam versus a
populated dict in the fragment, a different branch) as merely weak. That was a wrong-but-
compatible class of continuation living inside the map. A known conflict is now unsound at
every threshold, like an outcome conflict. 17 such joins on that seam alone moved from
accepted-SYMBOL to rejected.

Cases where `VALUE` is insufficient: zero-argument factories (`get_manager()`,
`TTSService.create()`, `ensure_backend()`) are vacuously `VALUE` for every fragment (38
alternatives on `get_manager`, 27 on `create`); their real selector is receiver/global state,
the `STATE` rung, which does not exist yet. Cases where `VALUE` decides: `_get_pipeline`
(`values differ: lang_code`, four `ARG_SHAPE` alternatives), `load_model` (`values differ:
path`), and every seam in the fixture and demo ground-truth cases below.

## Ground truth with path-level checks (Part 5)

Two cases have whole executions (`docs/runs/groundtruth/`). Edge level as before
(precision 1.000 on both; recall 1.000 after probes); new at path level:

| case | entry | truth seqs | claimed | matched | extra | missed |
|---|---|---|---|---|---|---|
| fixture, 6 unit tests | `place_order` | 2 | 3 | 0 | 3 | 2 |
| fixture, + probe | `place_order` | 2 | 3 | **1** | 2 | 1 |
| demo, probes only | `create_order` | 1 | 2 | 1 | 1 | 0 |
| demo, probes only | `read_inventory` | 2 | 1 | 1 | 0 | 1 |

Reading: on the fixture the one matched sequence is the full whole-execution path
`place_order → place → _validate → reserve → quote → price_for → price_for`, reachable only
after the probe supplied `reserve`, and composed entirely through `VALUE` seams; the two
*extra* sequences are the `ARG_SHAPE` alternatives (the empty-cart `quote` fragment and the
claim-less `place` fragment), paths the whole execution did not take. The missed sequence is
the raising branch (`place_order! → place! → _validate!`): no seed observed the entry raising,
and the one raising `place` fragment is (correctly) unsound against a returning stand-in. On
the demo, the extra `create_order!` sequence is real behavior the probe drove that the
ground truth did not (not a wrong composition); the missed `read_inventory!` branch is a
probe that only exercised the success path.

Seam-level lattice precision, all ground-truth seams: `VALUE` 5/5 matching, `ARG_SHAPE`
5/7 matching on the demo (where no value-dependent branch exists) and 0/2 on the fixture
(where one does). At path level the lattice separates cleanly: every extra path came from an
`ARG_SHAPE` seam; every matched path from `VALUE` seams.

## Language-neutrality after Python + Node + Go (Part 10)

Core files: `model.py`, `compose.py`, `resolve.py`, `graph.py`, `probe.py` (objectives,
verification), `llm.py` (writer seam), `projection.py`, `evaluate.py`.

| change | for | classification |
|---|---|---|
| `Symbol.kind` (`callable` / `declaration`) | Part 8 | genuinely missing universal concept (found on Python, applies everywhere) |
| type conflicts are unsound in `grade_seam` | Part 4 | composition semantics fix, runtime-neutral |
| `static-return-type` relation and resolver rule; `SymbolIndex.return_type_of` | Part 7 | universal concept (declared return types) behind the index seam; only the Python index extracts it today |
| `SymbolIndex.is_test` replaces "definition under a test root" | Go | **leaked Python/Node assumption**: Go tests live beside the code (`_test.go`) and doubles in generated packages; the core now asks the index |
| `--rev` workspaces from `git archive` | Go | neutral capability |
| `RuntimeAdapter` seam (from the Node pass) | Node | leaked assumption already fixed; Go plugged in with zero further changes to the seam |
| instrumenter, `dg` runtime, MockGen-header claims, `GOPROXY=off` execution, `-run DiffgenomeProbe` selection, probe re-instrumentation | Go | Go-only, all under `tools/go-collector` and `collect/go_test.py` |

Untouched by Go: the event protocol, resolver rules R1–R5, the composer and join lattice,
fragment merging, the graph and its JSON, objective selection and verification, the
report, the projection. The Go traces went through `execution_from_json` unchanged, after
one emitter fix on the Go side (two protocol fields must be present, not omitted).

Assumptions that remain runtime-specific: the raised/returned outcome model reads Go's
trailing `error` as "raised" (a convention, stated in the adapter); goroutine spawn
causality is not tracked (calls from spawned goroutines hang off the stimulus root); the
`STATE` rung is unimplemented everywhere.

Verdict, evidence-based: capture adapters differ substantially (sys.monitoring; TypeScript
source rewriting with AsyncLocalStorage; Go AST rewriting with named results and deferred
exits) while graph, provenance, composition and probe objectives were unchanged by Go. One
assumption leaked (test location), one universal concept was added (declarations), one
semantic error in composition was found and fixed (type conflicts). The seam held.
