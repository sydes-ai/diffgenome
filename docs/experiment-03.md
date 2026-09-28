# Experiment 03: the MVP on a real change

## Question

Given a real repository and a real code change, what part of the repository's behavior can
diffgenome reconstruct without running the real system, how does it know, where does
knowledge stop, and how much of the missing behavior can AI-generated *isolated* execution
recover under the security invariants?

## Setup

- Target: `Kokoro-FastAPI` at `5152e8b`, read-only. 318 unit tests, 92 async, spec'd mocks,
  `patch()` interposition, hand-written fakes.
- Change: commit `8307b0e` "optional model auto-unload after idle timeout", a merged
  feature touching `ModelManager` (150 lines), `TTSService`, the development router and
  tests. Diff-centred: 37 changed symbols, 23 in-repo seeds. Four changed symbols have no
  execution at all (`Settings`, `ModelManager` class body, `unload_all`, `reload`).
- Neighborhood: 3 hops upstream, 4 downstream, over observed and composed edges.
- Probes: up to 3 objectives, 2 attempts each; writer `gpt-5` (chosen from the account's
  model list); execution in a disposable workspace copy under macOS Seatbelt (no network,
  writes only inside the workspace, environment of seven variables, `ulimit`s), with the
  egress guard recording any connect attempt as OS-plane evidence.
- Run record with the report and the verbatim probes: `docs/runs/kokoro-8307b0e/`.

## Result

| metric (change neighborhood) | before | after 3 probes |
|---|---|---|
| observed edges | 70 | 78 |
| composed edges | 5 | 8 |
| strong joins (VALUE or better) | 1 | 6 |
| weak joins | 4 | 2 |
| internal gaps | 3 | 2 |
| unresolved boundaries | 15 | 17 |
| external boundaries | 11 | 11 |
| probe-derived edges | 0 | 16 |
| tests establishing the paths | 45 | 48 |
| reconstructed / provisional denominator | 71/93 = **0.763** | 84/105 = **0.800** |

All three probes were accepted on the first attempt, each on evidence from its own trace:
passed, executed the intended target as a real call, attempted no egress, and changed the
map.

| objective | what gpt-5 wrote | what the trace showed |
|---|---|---|
| gap `ModelManager.initialize` (reached only through a stand-in from `ensure_backend`) | patched `torch`, `KokoroV1` and `load_model`; drove the real `ensure_backend` | real `ensure_backend → initialize → _determine_device`; the seam `ensure_backend ⇢ initialize` now composes at `VALUE`; a new gap one level deeper (`initialize → KokoroV1`) appeared and was closed by probe 3's real `KokoroV1.__init__` |
| weak join `ensure_backend ⇢ load_model` (`ARG_SHAPE`) | a hand-written `StubBackend` fake; called the real `load_model` with the path `ensure_backend` passes (`manager._config.pytorch_kokoro_v1_file`) | `load_model` fragment with the same argument digest: the seam is now `VALUE` |
| weak join `generate_from_phonemes ⇢ KokoroV1._get_pipeline` (`ARG_SHAPE`, `values differ: lang_code`) | patched `KPipeline` (external) and `settings`; called `_get_pipeline("a")` | real `KokoroV1.__init__ → Settings.get_device`, `_get_pipeline` with the matching value: `VALUE` |

Denominator caveat, stated again because the number invites misuse: 93 → 105 counts the
seams we know about in the neighborhood (observed + composed + gaps + unresolved). It
grew *because* the probes introduced their own stand-ins (`StubBackend.load_model`,
`DummyPipeline.__init__`), which are real seams and are counted honestly. The signal in
this experiment is not the ratio moving from 0.76 to 0.80; it is strong joins going from
1 to 6 and gaps from 3 to 2 on the paths that matter for the change, with every new edge
marked `probe_derived` and traceable to a probe file, its execution, and its seam.

What remains, and why, is in the report: two gaps on `TTSService` construction (the class
has no in-repo `__init__`, so no probe can make it appear as a call; recorded as not
probeable), 17 unresolved stand-ins (8 hand-written fakes with no claim, 5 calls on the
return of a patched factory that only a static return type could resolve, `_backend`
attribute mocks whose type is only in an annotation), and 2 weak joins (`create ⇢
get_manager` at `SYMBOL` only, `generate_from_phonemes ⇢ get_voices_path` at
`ARG_SHAPE`).

## Findings

1. **Targeted probes recover the seams nearest the change first, and expose the next
   ones.** Probe 1 closed its gap and revealed `initialize → KokoroV1`; probe 3 closed that
   as a side effect. The loop's "measure, re-compose, pick again" shape is what made the
   second closure visible; a single-shot "write tests" request would not have reported it.
2. **The model was given the seam, not the repository.** Context per objective: target
   source, enclosing class and its `__init__`, the caller, the existing test that produced
   the seam (so literal argument values are available without the trace ever storing
   them), the substitutions active in that test, runtime outcomes, one nearby test file,
   conftest fixtures, pytest config. That was enough for 3/3 first-attempt acceptance on
   this target; it is one target and three objectives, not a rate.
3. **Verification, not trust, decided.** The first live pass had every probe fail with
   "no executions": the runner lacked `PYTHONPATH` for the collector plugin. Six drafts were
   written and none were accepted, correctly, because nothing in the map changed. The
   verdict never depended on the model's claim that the probe worked.
4. **Collector inconsistency found by the probe.** A patched *class* was claimed as the
   class, while a spec'd class stand-in was already claimed as its `__init__`. The probe's
   real `KokoroV1.__init__` could therefore not close the gap its sibling opened. Fixed
   in the collector (same rule for both paths); the definitive report is a deterministic
   replay of the same three drafts after the fix.
5. **Class construction with no in-repo `__init__` is not probeable** in this model: the
   class symbol never appears as a call. Objective selection now skips and reports it. The
   honest reading is that `TTSService()` here has no in-repo behavior of its own; what the
   routers reach is `TTSService.create`, which the map already covers.
6. **Probes add seams as well as evidence.** Every fake or patch a probe introduces is a
   stand-in in the probe's own execution and enters the denominator. That is correct
   accounting, and it means the ratio is a conservative measure of what probes do.
7. **Instrument facts.** `gpt-5` rejects any non-default `temperature`; a venv's
   `python` must be passed *unresolved* (resolving the symlink selects the base
   interpreter, which is why the first sandboxed run could not import `kokoro`); pytest's
   collector plugin needs `PYTHONPATH` inside the sandbox because nothing else is
   inherited; probes and traces must be written inside the workspace because the sandbox
   refuses everything else, which is the sandbox working.

## Answer to the question, for this change

Without running the real system: 70 observed and 5 composed edges around the change,
established by 45 existing tests, with 11 external boundaries where the code leaves the
repository (torch, kokoro's `KPipeline`, loguru, time). Knowledge stopped at 3 internal
gaps, 4 weak seams and 15 unresolved stand-ins. Three AI-generated isolated probes,
executed under confinement and accepted on their traces, turned 5 weak or missing seams
into `VALUE`-grade composed continuations and added 8 observed edges, leaving 2 gaps that
this model cannot probe and 17 unresolved stand-ins whose resolution needs static type
facts or remains genuinely unknown. Every edge in the report says which execution, seam,
fragment and rule it rests on.

## What this does not show

One change, one repository, three objectives, one model. No ground truth for whether the
composed paths are the ones production takes (experiment 05). No measure of how often the
writer fails on harder seams. No Linux OS-plane collector yet, so "no egress" rests on
Seatbelt plus the runtime guard rather than on kernel-observed syscalls.
