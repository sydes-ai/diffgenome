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
