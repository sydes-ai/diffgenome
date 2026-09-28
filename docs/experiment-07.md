# Experiment 07: the STATE rung, exit categories, and an adversarial ground truth

## What this pass asked

Experiment 06 ended with a named weakness: zero-argument factories (`get_manager()`,
`TTSService.create()`) were vacuously `VALUE` for every fragment, and the fixture ground
truth showed that `VALUE` seams can only be as right as the arguments are decisive. The
question here is narrow: **does a bounded, value-free STATE rung change what the composer
accepts, on a corpus built to fool VALUE, and on the real Kokoro corpus?** Secondary: exit
compatibility by category and identity rather than a returned/raised bit; a state-aware probe
objective; the privacy accounting for state. Concurrency causality was deferred by the brief
and is not touched. No LLM call was made in this pass: every replay used recorded drafts.

Artifacts: `docs/runs/exp07-state/` (adversarial evaluations VALUE-only and STATE, Kokoro
state comparison, Go and Node replays), `fixtures/exp07_state/`, `tests/test_exp07.py`.

## A. STATE design

A **state fact** is `(name, bucket, digest)`, the same triple as an argument shape:

| name | what | bucket |
|---|---|---|
| `self:type` | receiver's type | `obj:<Type>` + digest of the type name |
| `self.<field>` | first 16 receiver fields (`__dict__`, exported struct fields, own enumerable properties) | see below |
| `global.<name>` | module-level names the function's code reads (`co_names` ∩ module globals) | see below |
| `global.<Mod>.<attr>` / `global.<Class>.<attr>` | attributes read through an imported module or a class (`settings.STRICT`, `ModelManager._instance`) | see below |

Buckets are deliberately coarse and value-free: `none`; `bool:true/false`; `num:zero/pos/neg`;
`str:empty/nonempty`; `coll:empty/one/many`; `enum:<member>`; `obj:stand-in[:spec]`;
`obj:<Type>` (digest of the type name only). Callables, types and modules are behavior, not
state, and are never facts. Python captures all four rows; Node and Go capture `self:type` and
`self.<field>` (receiver only). What the seam side exposes:

| seam mechanism | state the seam records |
|---|---|
| instance-attribute stand-in (`patch.object(obj, "run")`) | the owner object's fields + the original member's module/class reads |
| patch-target on a module function | the original function's own module/class reads (its `__globals__`, not the module it was patched in) |
| patch-target on an instance | that instance's fields + the original member's reads |
| subclass fake (Python/Node) | the receiver's inherited fields |
| everything else | nothing (`state unavailable`) |

Compatibility is by name over the facts **both** sides observed: `match` (≥1 fact compared,
all equal), `conflict` (a compared bucket differs), `unavailable` (no common facts, or none
on a side). STATE sits above VALUE and is only consulted after VALUE holds; a conflict is
unsound at every threshold; `unavailable` leaves the join at VALUE with the note
`state unavailable on one side`. No fact ⇒ no upgrade.

## B. Outcome model

`Outcome` is `<category>[:<identity>]` with categories `returned`, `returned-error` (Go's
last-result error), `raised`, `panic`, `cancelled`, `unknown`. Join validity is **entry ×
exit**: `exit_compatibility` returns `same` (categories and known identities agree), `kind`
(categories agree, an identity unknown), `unknown` (an outcome unobserved), or conflict
(different categories, or two different known identities). `raised ValueError` vs
`raised KeyError` is a conflict; `returned-error` vs `panic` is a conflict. The Go collector
previously emitted both errors and panics as `raised:go:...`, so a category-only comparison saw
them agree; it now emits `returned-error:<type>` and `panic:<type>`. The verdict is on every
composed `Evidence.exit` and every `JoinAttempt.exit`.

## C. Adversarial ground truth (`fixtures/exp07_state`)

`Processor.run(item)`: `seen += 1`; if `not enabled` → `skip`; else `validate`, `audit` if
`settings.STRICT`, then `persist` (which `repo.save`s and raises `RepositoryClosed` when the
repository is closed). Every fragment calls it with the identical argument `"item-1"`.

Seed (`tests/test_pipeline.py`): a real `Pipeline` over a real `Processor(enabled=True)` whose
`run` is replaced on the instance, `STRICT=False`. Four fragments (`tests/test_processor.py`):
enabled-persists, strict-audits (`monkeypatch.setattr(settings, "STRICT", True)`),
disabled-skips, closed-repo-raises. Ground truth (`groundtruth/`, never in the corpus): three
whole executions of `Pipeline.execute`: enabled, strict, disabled.

What the seam and the fragments recorded (values never leave the process):

```
seam  self:type obj:Processor  self.repo obj:Repository  self.enabled bool:true  self.seen num:zero  global.settings.STRICT bool:false
persists   ...  self.enabled bool:true   global.settings.STRICT bool:false   returned
strict     ...  self.enabled bool:true   global.settings.STRICT bool:true    returned
disabled   ...  self.enabled bool:false  global.settings.STRICT bool:false   returned
closed     ...  self.enabled bool:true   global.settings.STRICT bool:false   raised:py:proc.repository.RepositoryClosed
```

Join matrix, seam `Pipeline.execute ⇢ Processor.run`, same corpus, STATE off then on
(`truth` = the candidate's first-level continuation is one some whole execution took;
`·` = rung not evaluated):

```
                        SYMBOL ARG_SHAPE VALUE STATE  EXIT      truth  accepted(VALUE-only)  accepted(STATE)
test_run_enabled_persists   ✓     ✓        ✓     ✓    same       ✓        ✓                    ✓
test_run_enabled_strict     ✓     ✓        ✓     ✗    same       ✓        ✓                    ✗  state conflict: global.settings.STRICT bool:false≠bool:true
test_run_disabled_skips     ✓     ✓        ✓     ✗    same       ✓        ✓                    ✗  state conflict: self.enabled bool:true≠bool:false
test_run_closed_raises      ✓     ·        ·     ·    conflict   ✓        ✗                    ✗  exit conflict: stand-in returned, fragment raised RepositoryClosed
```

Every candidate is a *true* continuation of `run` under some state, which is precisely why
`VALUE` cannot choose between them: the arguments are identical and the exit is `returned` for
three of them. Only the seam's state selects.

## D. Metrics

Path level (pre-order sequences from `Pipeline.execute`, depth 6), identical evidence corpus:

| ground truth | mode | truth | claimed | matched | extra | missed | path precision | path recall |
|---|---|---|---|---|---|---|---|---|
| seed's condition (enabled, STRICT=False) | VALUE-only | 1 | 3 | 1 | 2 | 0 | **0.333** | 1.000 |
| seed's condition | VALUE+STATE | 1 | 1 | 1 | 0 | 0 | **1.000** | 1.000 |
| all three conditions | VALUE-only | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 |
| all three conditions | VALUE+STATE | 3 | 1 | 1 | 0 | 2 | 1.000 | **0.333** |

Explanations the evaluator now prints per path:

```
extra  execute → run → skip:                                admitted at seam execute ⇢ run with join VALUE
extra  execute → run → validate → audit → save → persist → save: admitted at seam execute ⇢ run with join VALUE
missed execute → run → skip:                                candidate test_run_disabled_skips at ⇢ run rejected: state conflict: self.enabled bool:true≠bool:false
missed execute → run → validate → audit → save → persist → save: candidate test_run_enabled_strict_audits at ⇢ run rejected: state conflict: global.settings.STRICT bool:false≠bool:true
```

Edge level is blind to all of this (edge precision 0.571 / recall 1.000 in both modes against
the seed condition, 1.000 / 1.000 against all conditions): every edge exists somewhere.
The two rows of the second block are the honest cost of STATE: the corpus contains one seed,
run under one state; the strict and disabled *paths* are real behavior of the system, but
nothing observed `execute` under those states. VALUE-only claimed them and happened to be
right; STATE says "not established from this evidence", and the probe objective in §F names
what would establish it. This is the intended asymmetry: the reconstruction should never say
more than the seeds' states license.

Seam-level: STATE 1 seam, 1 consistent, 1 matching (seed condition). VALUE-only: 3 seams
accepted, 1 matching.

## E. Real-case replay

### Kokoro-FastAPI `5fb71ea` (Python), same 318 existing tests + the recorded probe

Whole graph, 711 join attempts, same corpus twice:

| | VALUE-only | VALUE+STATE |
|---|---|---|
| SYMBOL / ARG_SHAPE (state not consulted) | 152 / 130 | 152 / 130 |
| VALUE | 361 | 48 (`state unavailable on one side`) |
| STATE | – | 166 (`state matched`) |
| rejected | 68 | 215 (+147 `state conflict`) |
| composed edges (symbol pairs) | 14 | 14 |

STATE removed 147 candidate fragments and qualified 166, without removing any symbol pair:
the map's edges are the same, the *alternatives* behind them are fewer and graded. Where
state was unavailable (48 of the 361 former VALUE joins): stand-ins with no owner object and
no module reads on the seam side, and class-method receivers (`cls` is not captured).

The two seams named in experiment 06:

| seam | VALUE-only | VALUE+STATE |
|---|---|---|
| `⇢ voice_manager.get_manager()` (19 sites, 8 candidates each) | 152 accepted `VALUE` ("no arguments") | 133 `STATE` (`global.VoiceManager._instance` matched), **19 rejected** (`obj:VoiceManager ≠ none`: the singleton-already-built fragments against a seam where it was not) |
| `⇢ model_manager.get_manager(config)` (19 sites) | 152 `SYMBOL` (arity differs at the seam) | unchanged: STATE is never consulted below VALUE |
| `TTSService.create ⇢ …` (1 site, 27 candidates) | 27 `VALUE` | 27 `VALUE`, `state unavailable on one side` (class method; nothing captured for `cls`) |

The `_instance` fact only exists because state facts follow the original function's own
globals: `get_manager` is patched where it is *imported*, and the module it is patched in does
not contain `ModelManager`. Before that fix the seam side was empty at all 38 sites.

Change neighborhood (the 5 changed symbols): joins VALUE 2 + STATE 1 (was VALUE 3),
rejected 31 (was 12), gaps and boundaries unchanged, probe accepted as before; the
provisional structural ratio is unchanged at 0.875 → 0.909 after the probe, as it must be
(it counts symbol pairs, and no pair moved).

### simplebank `5b03c1d` (Go), re-traced with the new collector

Outcome categories in 50 existing executions: `returned` 1044, `returned-error` 27,
`unknown` 50 (test roots), no panics. 324 call nodes carry receiver state (13 repository
symbols, e.g. `api.Server.setupRouter: self.store obj:*mockdb.MockStore, self.router none`;
`token.PasetoMaker.CreateToken: self.symmetricKey coll:many`: a secret key is a length
bucket, nothing more). The recorded probes replay identically: `GetAccount` seam rejected as
`exit conflict: stand-in returned-error:go:*errors.errorString, fragment returned` (was
`outcome conflict: stand-in raised:go:...`); the `TransferTx` probe panics on a nil pool as
before (`docs/runs/exp07-state/go-replay/probe-0_1-transfertx.log`) and is rejected as a
failing probe, so no `panic` fragment enters the corpus. The error-vs-panic distinction is
therefore demonstrated at the model level (`tests/test_exp07.py::test_b1`): under the old
categories both were `raised`; now `returned-error:*errors.errorString` vs
`panic:runtime.errorString` is a conflict. No existing simplebank seam is of that shape.

### express-typescript-boilerplate `d77fe2a` (Node)

27 of 87 call nodes carry receiver state (`AuthService: self.log obj:LogMock,
self.userRepository obj:RepositoryMock`). The one composed seam is `ARG_SHAPE` (the
stand-in's argument is a mock), so STATE is not reached; metrics identical to experiment 06.

## F. Final assessment

1. **Does STATE exist as a real rung?** Yes: captured by all three collectors (receiver on
   all three; module/class reads on Python), compared by the composer above VALUE, visible
   in every join attempt, in evidence (`exit` and `join`), in the matrix and in the metrics.
   It is not an inferred upgrade: no common fact ⇒ VALUE with a note.
2. **Does it change what is accepted?** On the adversarial corpus: VALUE-only path precision
   0.333 → 1.000 under the seed's condition. On Kokoro: 147 of 711 candidates rejected,
   166 qualified, `get_manager()` went from 152 vacuous VALUE joins to 133 STATE + 19 rejected.
3. **Is the outcome model richer than a bit?** Yes: category × identity; Go errors and panics
   are distinct categories; `raised ValueError` ≠ `raised KeyError`.
4. **What does STATE cost?** Recall, when the seeds never ran under the fragment's state:
   all-conditions recall 1.000 → 0.333 on the fixture. That loss is reported per path with the
   rejecting fact, and becomes a probe objective, not a silent hole.
5. **Where is STATE unavailable?** Class-method receivers, seams whose stand-in has no owner
   object and whose original reads no module state, Node/Go module-level state (not captured),
   and every seam below VALUE (never consulted). Kokoro: 48 of the former 361 VALUE joins.
6. **State-aware probes?** A `state_condition` objective exists: when the real target ran
   but every candidate was rejected on state alone, the objective says "execute X with these
   arguments under state {self.enabled is bool:true, global.settings.STRICT is bool:false}"
   (`tests/test_exp07.py::test_d3`). It has not been exercised against the LLM (no calls this
   pass); whether a writer can set up that state from bucket names is untested.
7. **Privacy.** See "Privacy of state facts" in `docs/architecture.md` §8: raw values are
   read in the target process only, bucketed immediately, never serialized; digests only for
   type names; low-entropy values are exactly why buckets are used instead of digests.
8. **What is still not done.** Subclass-fake override claims via the MRO in the Python
   collector (Node has them); `cls` receivers; Node/Go global state; the state-condition
   probe against a live writer; concurrency causality (deferred by the brief).

Falsification note: the adversarial fixture was written to make VALUE fail and STATE
succeed; it proves the mechanism, not the prevalence. The Kokoro numbers are the prevalence
evidence, and there STATE's effect on the *change neighborhood* was one join qualified and
19 candidates dropped, not a different map.
