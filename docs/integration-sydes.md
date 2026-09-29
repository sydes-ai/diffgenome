# Integration: Sydes consuming DiffGenome

The transition from standalone research to product value. Sydes
(`~/StudioProjects/sydes`) gains one bounded capability, `verify-change --behavioral-map
diffgenome`, that consumes the `diffgenome-change/1` artifact (`docs/integration-artifact.md`)
and merges runtime/composed evidence with its structural view without flattening
provenance. Full record, artifacts and the before/after comparison live in the Sydes
repository: `docs/integration/diffgenome.md` and `docs/integration/diffgenome-simplebank/`.
Copies of the artifacts are under `docs/runs/integration-sydes/simplebank-5b03c1d/`.

## What was built

DiffGenome side (independently usable, unchanged core):

- `diffgenome change …` console script and `diffgenome.api.analyze_change(...)` /
  `load_change_artifact(path)`; `mvp` also writes the artifact.
- `src/diffgenome/change_artifact.py`: the bounded, deterministic projection. Tested on the
  experiment 07 fixture (`tests/test_change_artifact.py`): determinism, provenance (seed +
  fragment on a composed edge, STATE status, exit verdict, rejection reasons), no internals.

Sydes side (`src/sydes/behavioral/`, 5 modules, 7 tests):

- `diffgenome_adapter`: subprocess invocation (`SYDES_DIFFGENOME_COMMAND` or `diffgenome`),
  opaque `--behavioral-args`, artifact loading with format check; every failure is a typed
  `BehavioralUnavailable`.
- `merge`: static steps matched to runtime nodes by file + trailing symbol name; evidence
  classes `OBSERVED_RUNTIME`, `COMPOSED_{STATE,VALUE,ARG_SHAPE,SYMBOL}`, static-only steps,
  `GAP`, `UNRESOLVED`, `EXTERNAL`; runtime-only and static-corroborated flags; changed
  symbols the run did not see are listed, never dropped.
- `attach`: the single hook in `verify-change` (after structural analysis, before AI
  recovery); the executing tests become `supporting_tests` on the change's required
  obligations with `match_rule=diffgenome:observed-execution` (supporting, never verifying;
  verdict unchanged); unavailable ⇒ explicit status and note.
- `render`: terminal section "Behavioral effect (executed evidence)" and the
  `### Behavioral effect` Markdown block (`python -m sydes.behavioral.render result.json`).

## Result on simplebank `5b03c1d`

See the comparison table in Sydes. In one line: Sydes went from "no existing verification
evidence; 2 changed symbols reach no entrypoint" (after 33 model calls of AI recovery that
rejected the very test) to "11 existing tests exercise this flow, entry via `authMiddleware`,
`TransferTx` is a gap, `New → TransferTx` is possible only", with 0 DiffGenome model calls
and 19 s of DiffGenome runtime. Verdict unchanged by design.

## Integration boundary: recommendation

**A. Sydes invokes the DiffGenome CLI (subprocess → artifact), with B's loader kept.**
This is what was built and it held up:

- *Coupling*: one JSON contract, versioned by name. Sydes imports nothing from DiffGenome;
  the same code path consumes a pre-built artifact (`--behavioral-artifact`), which is how CI
  will use it (DiffGenome runs where the target's tests can run).
- *Versioning*: `diffgenome-change/1`; additive changes are free, re-meaning bumps the
  number; the loader rejects anything else with a reason.
- *Runtime dependencies*: DiffGenome needs the target's toolchain (Go, the target venv, Node)
  and its own sandbox; Sydes needs neither. A library import would drag DiffGenome's
  collectors and sandbox into Sydes' process and packaging for no gain.
- *Failure isolation*: a collector crash, an unsupported runtime, a hung test suite are a
  non-zero exit or a timeout in a child process; the structural result is untouched and the
  report says why (tested).
- *Testability*: the merge and renderers are tested against a synthetic artifact; the
  adapter's failure modes against a missing binary and a foreign file; DiffGenome's artifact
  against its own fixture. No test needs both repositories.
- *Deployment*: `pip install diffgenome` (or a pinned wheel) next to Sydes in the CI job,
  or DiffGenome as its own job uploading the artifact. No service, no shared process.

B (library) is worth keeping only as the artifact loader (it exists: `diffgenome.api`). C (a
service) has no demonstrated need: the artifact is small (13 KB here), produced once per
change, and consumed once.

## Deferred (recorded, not done)

Linux OS plane; Java/Rust; more framework support; more STATE research; Node/Go global state;
`cls` receivers; MRO edge cases; concurrency causality; UI; graph database; production
sandbox hardening; benchmark scaling. Integration-specific next steps: make the sydes-action
renderer read `supporting_tests`/`behavioral` (its "regression test: Not found" row is now
contradicted by the section above it); let AI recovery's trigger consult behavioral evidence
(it re-spent 47 model calls on a question DiffGenome had answered); a probe-budget policy
keyed to gaps at distance ≤ 1 from the change.

## Second pass: making the integration trustworthy (2026-09-29)

Follow-ups from the first pass, all in place and tested:

- **Sydes' AI recovery consults executed evidence.** A gap the behavioral run already
  answers is not sent to the model. On simplebank that removed AI recovery entirely: 0
  recovery model calls, down from 33 before and 47 in the first after run. On Kokoro,
  recovery that had triggered and failed was not needed. The "entry path" rule is strict:
  a changed symbol counts as reached only when observed or reconstructed calls connect it to
  a step of Sydes' own flows. Reaching a service method its unit tests call does not count.
- **The PR comment (sydes-action renderer, local clone, not pushed)** gains
  `### Behavioral effect`. The regression-test row, a new "Executed in isolation" row, the
  named-test rows and the before-merging nudge now read the evidence consistently.
  Observed tests are never shown as "Checks the behavior: Yes".
- **Composer fix: arguments aligned by name.** Found on Kokoro PY-H-01. A route called
  `TTSService.generate_audio` by keyword while the fragment recorded the signature order,
  including a defaulted parameter. Positional pairing produced a spurious type conflict and
  rejected a real route-to-service continuation. `compose.align_arguments` now pairs by name
  when both sides carry real parameter names. A parameter present on one side only caps the
  join at ARG_SHAPE. Experiment 07's Kokoro VALUE-only/STATE figures are unchanged,
  re-measured on the same corpus: that measurement composed without the static-return-type
  rule, and the misaligned seam exists only with it.
- **Artifact additions (still `/1`, additive):** per-execution `file` (a Go subtest id has
  none of its own) and `outcome`; `budget.probe_max_distance`; and `diffgenome-status.json`
  (`refused` / `failed` with a reason) whenever no artifact is produced.
- **`change` defaults for integrators:** `--up 5`, so a deep change meets its entry point;
  `--probe-max-distance 1`, so probes are spent only on gaps next to the change, with the
  rest listed in notes.
- **No sandbox, no run:** on a host without a supported OS sandbox, which today means any
  Linux runner, `change` exits 3 with one line of reason and a status file. It never runs
  target tests unconfined. Sydes shows that reason.
- **CI, checked locally only:** `sydes/docs/integration/ci-local-simulation.sh` reproduces
  the two-job hand-off, with DiffGenome uploading and Sydes consuming via
  `--behavioral-artifact`, plus the Linux refusal leg. Both behave as designed. A real
  GitHub run was not attempted. Docker is not running here, and a Linux runner would only
  demonstrate the refusal. The blocker for CI is a Linux sandbox for DiffGenome, which is
  on the deferred list.

Second validation case: Kokoro-FastAPI PY-H-01, in `sydes/docs/integration/diffgenome-kokoro/`.
