# Experiment 04: a second runtime (Node/TypeScript)

## Question

Does the diffgenome abstraction survive a second runtime without changing the core model?
Concretely: a Node collector emitting the existing event protocol, consumed unchanged by
the existing graph, composer, change-centred analysis, probe loop and report.

## Target

`~/sample_repos/express-api-starter-ts` (the staged target) was unsuitable: no
`node_modules`, and no stand-ins at all (two supertest tests over 8 files), so composition
would have had nothing to exercise. Substituted **`express-typescript-boilerplate`**:
60 source files, 5 unit suites / 13 tests, hand-written fakes (`RepositoryMock`,
`EventDispatcherMock`, `LogMock`) wrapping `jest.fn()` stand-ins, Jest 23 with the
repository's own TypeScript preprocessor, dependencies installed. One environment repair,
recorded as an external substitution: `bcrypt@3.0.1`'s native binding does not build on
Node 22, so the workspace Jest config maps `bcrypt` to the pure-JS `bcryptjs` (only
`User.hashPassword/comparePassword` reach it; a true external). The target repository is
never written to; the workspace copy is instrumented in place and destroyed.

Change: commit `d77fe2a` "Reject non-positive pet ages" (real, local): `PetService.create`
throws `InvalidPetAgeError` when `age <= 0`, plus a regression test. Diff-centred.

## Node collector

`tools/node-collector/` (own pinned TypeScript 5.9; no dependency on the target's compiler):

- `instrument.js` rewrites every `.ts/.js` under the source and test roots of the
  workspace copy: each function body gets entry/return/throw reporting; sync functions keep
  `this`/`arguments` via try/catch/finally; **async functions and generators have their
  body moved into a callback run under `AsyncLocalStorage`**, which is what makes caller
  attribution across `await` correct (the caller's store is restored on the synchronous
  return, continuations keep the body's store). Call sites become `__dg.callm(obj, "m",
  [args])` / `__dg.callf(f, [args])` so calls into `jest.fn()` stand-ins are recorded with
  their arguments and outcomes. Named classes are registered with their symbol. It also
  emits the symbol index (definitions with line spans, against the original sources) the
  Python side uses for diff mapping and probe context.
- `runtime.js` builds one protocol `Execution` per test: `CallNode`s with args
  `(name, shape, digest)`, outcomes `returned` / `raised:<Error type>` (promise-returning
  calls settle their outcome on resolution/rejection: the same settlement semantics the
  Python coroutine frames give), `SubstitutionNode`s for `jest.fn()` (`mock_object`) and
  for test-defined functions entered from repo code (`fake`/`stub`, non-leaf), an OS-plane
  egress guard on `net.Socket.prototype.connect` (loopback allowed and recorded, anything
  else refused and recorded). Observer integrity: every host function it needs is bound at
  load time, so a target's later patches of `fs`, `crypto` or globals cannot redirect it.
- `jest-setup.js` marks each spec as a stimulus (jasmine2 reporter on Jest 23,
  `beforeEach/afterEach` on jest-circus) and chains the target's own setup file.

**Deterministic claim found on this target.** `LogMock extends Logger` and overrides
`info`. On entering a test-origin method, the runtime walks `this`'s prototype chain for
the nearest registered repo class that defines the same member: `LogMock.info` claims
`Logger.info` with relation `overrides`. Identity through the prototype chain, not a name
match. (`RepositoryMock`/`EventDispatcherMock` have external base types, TypeORM and
event-dispatch, and correctly stay unresolved.) The Python collector does not yet apply the
same rule to subclass fakes via the MRO; recorded as a follow-up.

## Existing tests under diffgenome

```
tests traced           13 (all passed), 0 collector failures
in-repo call nodes     74     symbols 50 (16 repo, 33 test, 1 external)
outcomes               returned 73, raised 1 (the new validation path), unknown 0
substitution nodes     30: 15 fakes, 15 jest.fn stand-ins
resolutions            internal 10 (claim-member via `overrides`), unresolved 20 (no-claim), external 0
join attempts          0 (no existing test executes any claimed target, e.g. the real Logger.info)
graph                  49 observed edges, 5 internal gaps, 10 unresolved boundaries
async/causality        0 attribution defects found: after `await this.userRepository.save(...)`
                       the following `dispatch` is attributed to `UserService.create`
egress                 0 attempts (13/13 executions report egress_attempts=0)
```

Traces are read by the unchanged Python `execution_from_json`; the graph, composer,
resolver, neighborhood, map slice and report ran without modification.

## Change-centred run and probes

Neighborhood of the 3 in-repo seeds (`PetService.create`, `InvalidPetAgeError.constructor`
and the test-file change is filtered out): 7 observed edges, 1 internal gap
(`PetService.create → Logger.info`, via the override claim), 2 unresolved fakes, ratio 0.700.

| | before | after 1 accepted probe |
|---|---|---|
| observed edges | 7 | 9 |
| composed edges | 0 | 1 (`PetService.create ⇢ Logger.info`, `ARG_SHAPE`) |
| strong joins | 0 | 0 |
| weak joins | 0 | 1 |
| internal gaps | 1 | 0 |
| unresolved boundaries | 2 | 3 (the probe's own winston mock) |
| probe-derived edges | 0 | 4 |
| provisional ratio | 7/10 = 0.700 | 9/13 = 0.692 |

The accepted probe (`docs/runs/node-d77fe2a/probes/probe-0_2.accepted.test.ts`) mocks
`winston` at module level, constructs a real `Logger` and calls the real `info`, which the
trace shows running `Logger.log → formatScope` before the stand-in. The seam grades
`ARG_SHAPE` only because the probe's arguments (`'hello', 42`) differ from the seed's; the
ratio fell because the probe's mock is a new unresolved seam, counted honestly.

Model calls on this target: **8** (4 runs × 2 attempts while the loop itself was being
fixed), **1 accepted**, 7 rejected, 4 verified new edges, 1 gap closed. Two of the
rejections were the loop's fault, not the model's: Jest reports on stderr and the
failure tail read stdout, so attempt 2 received no failure detail; and the target's private
delegate (`Logger.log`) was outside the context, so the model guessed winston's shape.
Both fixed in runtime-neutral code (failure text from whichever stream holds the report;
enclosing class source in full, bounded). Two rejections were the model's: `jest.isolateModules`
does not exist on Jest 23, and an import path one level short; the adapter now states the
exact relative import path and the Jest-version API caveats.

## Language-neutrality test: what changed, and where

Changes to **core types and semantics** (`model.py`, `compose.py`, `resolve.py`,
`graph.py`): **none.** Node emits new *values* of free-form fields the protocol already had:
symbol prefix `js:`, relation `overrides`, substitute `js:jest.fn`, OS event outcome
`allowed:loopback`, exception symbols `js:TypeError`.

Changes elsewhere, classified:

| change | classification |
|---|---|
| `RuntimeAdapter` / `SymbolIndex` seam (`runtime.py`); `ProbeRunner` no longer builds a pytest command; `--runtime` in the CLI | **Python assumption leaked into the pipeline layer**: the probe loop and CLI were pytest-shaped. Now behind an adapter, with `collect/py_runtime.py` and `collect/node_jest.py` as the two implementations. |
| Probe context derived the module by `rsplit(".", 2)` of a Python qualname; conftest fixtures and pytest config were assembled in the neutral context builder | **Python assumption leaked**: module derivation is now `index.module_of`, conventions come from the runtime adapter. |
| Probe writer system prompt said "pytest test file" and forced `test_*.py` filenames | **Python assumption leaked**: the request now carries the adapter's conventions; the harness places the file. |
| Test-root symbol filter compared `py:` prefixes as strings | **Python assumption leaked**: now decided by the index (definition path under a test root). |
| Sandbox: loopback sockets allowed for the runtime that needs them; process limit raised | **Genuine universal concept** (loopback is not egress; Python's `TestClient` never opened a socket, Node test servers do) and one instrument fact (`ulimit -u` on macOS counts the whole user). |
| Override-based claims for subclass fakes | **Genuine universal concept** surfaced by Node, implemented in the Node collector; Python collector to follow. |
| Enclosing-class source in probe context; failure text from the right stream | **Neutral improvements** to the probe loop found by the Node run. |
| Instrumentation, ALS attribution, Jest hooks, class registration, bcrypt shim, Jest-23 caveats | **Node-only implementation detail**, all under `tools/node-collector` and `collect/node_jest.py`. |

Verdict: the core protocol and reconstruction survived a second runtime unchanged; four
Python assumptions had leaked into the probe/LLM/CLI layer and are now behind the runtime
seam; two universal concepts (loopback, override claims) were found rather than invented.

## What this does not show

One Node target with 13 tests and no existing execution of any claimed target, so zero
join attempts from existing tests; composition on Node was exercised only through the
probe-created seam. No vitest / jest-circus target was run (the setup path for jest-circus
is implemented but untested). `jest.mock(module)` automocks and `jest.spyOn` claims are not
extracted (no target used them). Overhead was not measured (the suite takes 0.7 s).
