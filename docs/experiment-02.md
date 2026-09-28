# Experiment 02: the VALUE join, and what a real target looks like

## Questions

**Q1.** Can a bounded content digest of arguments at seams let the composer select among
fragments that `ARG_SHAPE` cannot separate, without capturing raw values?

**Q2.** Does reconstruction survive a less artificial target than the fixture, and what
breaks it? (The staged target was `fastapi-cross-file`.)

## Findings log

### 2026-09-28: the staged target has nothing to compose

`~/sample_repos/fastapi-cross-file` has two source files, one endpoint that copies a
validated pydantic payload into a response, **no tests, no virtualenv, no git history**.
There is no stimulus, no stand-in, no seam, and no in-repo branching. It cannot exercise
composition or the `VALUE` join, and adding a test to it would be probe generation
(experiment 04) in disguise. The only in-repo behavior it has is one call; everything
else (validation, serialization) is framework-owned, which is finding 2 of experiment 01
again. Nothing was done to it.

What this changes: Q2 needs a target that already has tests with stand-ins. Q1 was run
on the fixture, where a value-differentiated seam exists by construction, with
`demo-orders-api` as the check that digests behave on real values.

### 2026-09-28: VALUE join

Protocol change: each argument entry becomes `(name, shape, digest)`; `digest` is a
sha256-derived content digest of the value to depth 3 and width 16 (scalars, containers,
dataclasses), all-or-nothing (any unsummarizable part yields `""`), never the value
itself. `CallNode.result` and `SubstitutionNode.result` carry the same digest of the
returned value. The composer grades `VALUE` only when every observed position has equal,
non-empty digests on both sides and outcomes are known-compatible.

| Prediction | Outcome | Evidence |
|---|---|---|
| **P10** at `min_join=VALUE` exactly one `quote` fragment composes, the one whose entry values equal the stand-in call | **holds** | `test_quote_sums_repository_prices` → `VALUE`; `test_quote_empty_cart_is_free` rejected, `values differ: skus`. `ARG_SHAPE` had graded both equally. |
| **P11** the three `place` fragments grade `VALUE` / `ARG_SHAPE` / unsound | **holds** | controller test (`"c-1", ["A","B"]`) → `VALUE`; unspecced test (`"c-2", ["C"]`) → `ARG_SHAPE`, `values differ: customer_id, skus`; raising test → unsound. |
| **P12** some real values are unsummarizable and the composer caps at `ARG_SHAPE` with the reason | **holds** | On `demo-orders-api`, pydantic `OrderCreate` arguments digest to `""` (`value unavailable`); `str` SKUs digest identically across four executions and differently for `"UNKNOWN"`. |

Core-model issue exposed, and what was changed:

**Causality after the seam.** Entry compatibility (the grade) says the fragment could
continue from the seam. It says nothing about the seed's own continuation *after* the
seam, which ran on the value the stand-in fabricated. In the fixture the stand-in for
`quote` returned 2500 and the real fragment also produced 2500, by authoring
coincidence; the empty-cart fragment produced 0. Before this change nothing recorded
either. Now `result` digests are captured for every call and stand-in call, and each
`JoinAttempt` reports `result_compatible` (True / False / None) with the note
`result differs: seed continued on it`. It is **not** a join grade: the lattice grades
the seam's entry; result compatibility is an independent axis about the seed's suffix.
Open modelling question, recorded rather than solved: the seed's edges after a seam are
`OBSERVED` (they did run), but they ran under a fabricated value. The composed tree does
not yet mark them as conditioned. A future evidence qualifier ("observed under
substituted result") would make that explicit; it is not added until a target shows a
case where it changes a conclusion.

Observations, not pass/fail:

- Digest availability on `demo-orders-api`: 5 of 16 argument positions are pydantic
  models and unavailable. Dataclasses digest; pydantic models do not because the digest
  scheme knows nothing about them. A language-neutral protocol cannot enumerate model
  libraries; the honest generalization is "objects with a stable field mapping", which
  the Python adapter could approximate by `__dict__`, at the cost of hashing internal
  state. Not done; the `""` is the correct answer until then.
- Short scalars are trivially reversible from digests by brute force. The digest keeps
  values out of casual reading of traces, not from an adversary. Acceptable for a
  research prototype; the trace store is inside the sandbox boundary anyway.

## What remains of experiment 02

Q2 still needs a real Python target with tests that use stand-ins. `fastapi-cross-file`
is not it. Candidates already under `~/sample_repos`: `flask-sample-app`,
`school-portal-api`, `SimpleFastPyAPI`, `healthchecks` (larger). Selection criterion:
existing tests with `unittest.mock`/`pytest-mock` usage against in-repo classes, so
resolution rate by rule, gap counts and the falsification list (async, generators,
`patch()`, fakes, dynamic dispatch) can be measured rather than assumed.

### 2026-09-28: first real target, Kokoro-FastAPI (Q2)

Selection: of the staged candidates, `flask-sample-app` and `school-portal-api` use no
stand-ins (their `patch(` hits are Flask routes) and `SimpleFastPyAPI` has no tests.
`Kokoro-FastAPI` (107 source files, 318 unit tests, 92 async, `Mock(spec=…)` and
`patch("api.src…")` against in-repo code, a working venv) is the smallest target whose
stand-in mix is the falsification list. `healthchecks` (Django, 346 in-repo `patch`
targets) is the follow-up. Target read-only; its `--cov` disabled under trace so two
tracers don't compete; overhead 2.06 s → 2.35 s.

| Prediction | Outcome | Evidence |
|---|---|---|
| **P13** async breaks shadow-stack attribution; repairs > 0 and calls misattributed under suspended coroutines | **mechanism confirmed, magnitude overstated** | Stack repairs: 6 in 4 executions. Frame-ancestry attribution disagrees with the shadow stack on **49 calls in 13 executions** (4%), all in generator/async `tts_service` tests. Repairs undercount misattribution by 8×, as reasoned: a call parented under a suspended frame returns in order. The collector now attributes by real frame ancestry; the shadow stack remains only as this diagnostic. Coroutine *scheduling* is a spawn relation like the thread hop: when the loop resumes a task, its creator is not on the stack (spike confirmed). |
| **P14** resolution dominated by `no-claim`; spec'd stand-ins resolve | **holds, then changed by the predicted rule** | Before: 306/336 (91%) `no-claim`, 29 `claim-member`. `patch()` installs spec-less mocks, but the patcher keeps the original object, so the claim is a fact. With the `interposition` mechanism and `patch-target` relation: **internal 108 (32%), external 34 (10%), unresolved 194 (58%)** = `no-claim` 125 + `claim-return-chain` 61 + `claim-unknown-origin` 8. |
| **P15** a fragment gap or identity mismatch from the `api.src` layout | **an identity mismatch, different cause** | `build_corpus` raised `IdentityMismatch` on `handle_url.<locals>.<lambda>`: two lambdas in one function share a qualname. Anonymous code now carries its definition line (`<lambda>@341`); the same numbering problem exists for Java `lambda$0`, Go `func1`, Rust `{{closure}}`. |

Core-model and instrument findings:

1. **The observer was hijacked by the observed.** Two traces were structurally different
   between identical runs. Both tests `patch("os.path.join")`. The collector named
   symbols through `pathlib`, which calls `os.path.join` dynamically, so
   `load_openai_mappings` was named after the test's temp file
   (`py:/.private.var/…/pytest-78/…/test_mappings.load_openai_mappings`), differently per
   run, and the per-code scope cache froze the wrong name. **Principle:** an in-process
   collector must not read patchable globals on its capture path. Scoping is now pure
   string work on prefixes computed at construction; `inspect` and `os.path` are gone
   from the capture path. Pinned by a test that patches `os.path.join`. This is a
   language-neutral hazard for every in-runtime collector (JVMTI agents share the JVM
   with Mockito; V8 hooks share the isolate with jest), and an argument the OS plane
   has for itself: a ptrace/eBPF observer shares no state with the target.
2. **Fan-out.** Composing every seed against every fragment produced 11,524 composed
   edges from 3,324 observed (`get_manager()` alone: 5,168 joins). Fragments were
   grouped by *behavior shape* (symbols, kinds, outcomes, claims, paths; not values):
   `conditional_int` had 261 fragments and 1 shape, `_render` 213 → 50, `normalize_text`
   97 → 19. Shape merging brings composition to **406 composed edges**; merged
   fragments are kept as `Evidence.alternates`, so provenance is complete. A shape is
   a behavior path, which is what the "genome" idea was about.
3. **Vacuous VALUE.** 21 `list_voices()` seams were graded `SYMBOL` with "no argument
   shapes on one side". With no arguments on either side, argument compatibility holds
   vacuously; the seam now grades `VALUE` with the note `no arguments`. It exposes what
   the lattice already said: for zero-argument calls, entry compatibility is entirely
   receiver/global state, the `STATE` rung. On this target 1,490 of 2,050 attempts are
   such vacuous `VALUE` joins on factories like `get_manager()`; they are honest about
   arguments and silent about state.
4. **Stand-in arguments compared as types.** `process_and_validate_voices(TTSService)`
   seams reported `type conflict: TTSService≠stand-in`. The stand-in was a
   `Mock(spec=TTSService)`; the conflict was the test's, not the seam's. Shapes of
   stand-in arguments now carry their spec (`stand-in:TTSService`) and compare as that
   type; a spec-less stand-in is a wildcard and caps the grade at `ARG_SHAPE`.
5. **Return chains are the next resolution frontier.** 61 stand-ins are calls on the
   *return value* of a patched factory (`get_tts_service.().list_voices`). The claim
   names the factory; what it returns is a static fact (`-> TTSService` annotation) that
   the runtime never observed. That is the `injection-annotation` rule family, and it is
   the first place static evidence would enter the graph, as `STATIC`, never as observed.
6. **Determinism on a real target.** After fix 1, 0 of 318 traces differ structurally
   between runs; 18 differ only in digests of values that are nondeterministic in the
   target (temp paths, timings, encoded audio). Repeated runs therefore identify
   *unstable values*, exactly the ones no seam should be graded `VALUE` on. Not acted
   on yet.
7. Smaller instrument facts: 1 of 318 tests failed under trace only because its
   parametrized id exceeded the filename limit (S1 doing its job); two parametrized ids
   collided after sanitizing and one trace silently overwrote the other. Trace files now
   carry a digest of the test id.

Numbers for the record (after all fixes): 318 executions, 3,324 in-repo call nodes on
2 threads, 508 symbols (149 repo, 334 test, 24 external, 1 unknown), 336 stand-in calls
(181 interposition, 83 fakes, 72 mock objects), 207 fragment targets, 11 gaps (7 are
construction of `TTSService` itself), 34 joins rejected as unsound (outcome conflict),
2 executions with no in-repo call.

What this changes in the plan:

- The remaining 58% unresolved splits into three named problems: spec-less injected
  mocks (125; needs `injection-annotation` or an LLM hypothesis), return chains (61;
  needs static return types), and 8 claims on objects whose module has no file. Each is
  now measurable per target, which is what experiment 02 was for.
- The OS plane gains a concrete argument (finding 1). Its collector and the sandbox stay
  next.
- `healthchecks` is the next target: 346 in-repo `patch` targets against a Django
  codebase will stress `interposition` and identity at scale.
