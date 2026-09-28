# Architecture

diffgenome is a **language-neutral runtime behavioral reconstruction system**. Its input is
an executing process plus a stimulus. Its output is a normalized execution graph that can be
composed across isolated runs, with the provenance of every edge intact. Python is the first
capture target, not the architecture.

## 1. Goal and non-goals

**Long-horizon goal.** For a change-centred region of a repository, reconstruct 85–90% of
the *locally realizable in-repo behavioral structure*, without the real application
environment, while recording exactly which parts were observed, composed, inferred or
unresolved.

Not 90% of production reality: that needs production state and external systems and can't
be guaranteed. The target is the behavior recoverable from source + isolated execution +
generated unit probes.

**North star metric.**

```
For a change-centred region R of the repository:

    reconstructed(R) = edges of R with evidence OBSERVED or COMPOSED(join ≥ ARG_SHAPE)
    denominator(R)   = edges of R that are locally realizable

Target: reconstructed / denominator ≥ 0.85, with every remaining edge explicitly
        marked STATIC / INTERNAL_GAP / UNRESOLVED_BOUNDARY, never guessed.
```

The denominator is the hard part of this definition. "Locally realizable" excludes edges
that only exist with production state or a real external system. Until experiment 05 gives
us ground truth on a repo that *can* run end to end, any number we report is a
**provisional reconstruction ratio** against whatever static call graph we used for R. It
is not a bound in either direction: a static analyzer for a dynamic language both misses
edges (reflection, dynamic dispatch, generated code) and invents edges (imprecise
resolution), and we don't claim over-approximation unless the analyzer used guarantees
it.

## 2. Invariants

These don't change as evidence comes in. Implementation strategy can.

| | Invariant | Enforced where |
|---|---|---|
| I1 | **No full-environment dependency.** No staging, no "just start Postgres/Kafka/Redis", no recreating the microservice environment. | design; sandbox has no route to any of them |
| I2 | **No language-specific core.** Collectors may differ completely; they emit one protocol. `model.py` mentions no language, framework or mocking library. | `model.py`; code review |
| I3 | **No hidden evidence upgrades.** Every edge carries its `EvidenceKind`; a composed or sampled edge is never displayed, stored or counted as observed. | `Evidence.__post_init__`; renderer |
| I4 | **No external side effects.** Target code and generated probes run in a sandbox with no egress, no secrets, resource limits, disposable workspace (§8). | sandbox |
| I5 | **No modifying target repos.** Targets are read-only; probes go into a temporary copy or worktree. | sandbox mount mode |
| I6 | **No claiming reconstructed = observed.** A reconstructed path is a tree of fragments joined at marked seams, never a flat end-to-end path. | renderer; graph API |

## 3. The two planes

At runtime every language becomes a process. Two things are observable about it, and they
have very different properties.

```
                          APPLICATION PROCESS
   ┌──────────────────────────────────────────────────────────┐
   │  SYMBOL PLANE      logical functions, calls, returns,    │
   │  (per runtime)     exceptions, threads                   │
   │                                                          │
   │  OS PLANE          syscalls, sockets, files, processes,  │
   │  (universal)       native calls, loaded libraries        │
   └──────────────────────────────────────────────────────────┘
```

**OS plane.** Kernel-visible: `connect`, `openat`, `execve`, `clone`, socket state,
`/proc/PID/maps`, native symbols via ELF/DWARF. Language-independent by construction. It
gives us *physical boundaries* (the process tried to leave) and native call structure. It
is ground truth for "did this code try to reach outside", and it's how the sandbox turns
external access attempts into evidence instead of letting them through.

**Observer integrity.** An in-process collector shares the runtime with the target, and
targets patch globals: on Kokoro-FastAPI a test's `patch("os.path.join")` reached into the
collector's `pathlib` calls and renamed symbols after the test's temp file. Capture paths
therefore read no patchable globals (no `os.path`, `pathlib`, `inspect` at event time). The
OS plane does not have this problem, which is one of its arguments.

**Symbol plane.** The program's own call structure. For native code this coincides with the
OS plane (addresses → ELF/DWARF → functions). For managed runtimes it does not, and that's
a fact about computation, not a tooling gap: from the CPU's point of view an interpreter's
logical program is **data, not code**. The instruction pointer sits in
`_PyEval_EvalFrameDefault` for every Python function; the logical stack lives in
heap-allocated frame objects. Under a JIT the address→function mapping exists but is
dynamic, per-process, and discarded on deoptimization. So the symbol plane always needs
the runtime's cooperation: exported metadata (perf maps), exported probes (USDT), in-runtime
hooks, or external reading of the runtime's data structures.

Neither plane is "the tracer". Every `Collector` declares its plane and its fidelity, and
every node records which collector produced it. A reader can always tell a sampled perf
stack from a complete `sys.monitoring` trace from a syscall log.

### Sampling cannot reconstruct paths

`perf record`, LBR call graphs and async profilers are **sampling**: "this stack was live at
instant *t*". Unit tests run for milliseconds; at 10 kHz a 5 ms test yields ~50 samples,
misses most functions, and gives no ordering between samples. LBR is a 16–32 entry ring
buffer captured *at each sample*, not a continuous record. Sampled data is still evidence
(`OBSERVED_SAMPLED`: callee was on the stack under caller), but path reconstruction needs
complete tracing, and the protocol keeps the two apart.

### Capture ladder

| Mechanism | Plane | Completeness | Overhead | Applies to | Portability |
|---|---|---|---|---|---|
| syscall tracing (ptrace/strace, eBPF tracepoints, seccomp-notify) | OS | complete | low–moderate | any process | Linux; macOS has dtruss under SIP limits |
| uprobes / uretprobes | OS→symbol | chosen native functions | ~1 µs/hit (trap) | any native symbol incl. runtime internals | Linux; uretprobes crash Go (stack copying) |
| USDT via eBPF | symbol | semantic events | low–moderate | runtimes built with probes (CPython `--with-dtrace`, HotSpot `ExtendedDTraceProbes`, Node) | Linux; opt-in build; JVM variant very slow |
| compiler instrumentation (LLVM XRay, `-finstrument-functions`, `-fsanitize-coverage`) | symbol | every entry/exit | near zero off | C/C++/Rust, partly Go | needs rebuild; fine for tests |
| Intel PT | OS+JIT | every branch | 2–5% record, decode ≫ | native + JIT with perf-map | Intel bare metal only; not AMD, not Apple Silicon, rarely VMs |
| DBI (Pin, Valgrind, DynamoRIO) | OS | every instruction | 5–50× | any native process | sees the interpreter, not the program |
| perf sampling + perf-map (`PYTHONPERFSUPPORT`, `-XX:+DumpPerfMapAtExit`, `--perf-basic-prof`) | symbol | **sampled** | low | Python 3.12+, JVM 17+, V8 | Linux |
| external frame reading (py-spy/Austin style) | symbol | sampled | low | one runtime each | reads runtime data structures |
| in-runtime hooks (`sys.monitoring`, JVMTI, V8 Inspector, Go `runtime/trace`) | symbol | complete | low–moderate | one runtime each | per-language |

Native-code caveat: with optimization on, "call/return" is itself a compiler artefact.
Inlining removes calls, tail-call elimination removes returns, identical-code folding merges
functions. DWARF inline tables recover part of it. Debug builds for unit tests sidestep it,
and that's acceptable, but it means "the call tree" is a debug-build notion.

Platform note: this project is developed on macOS, where perf, eBPF, uprobes and PT don't
exist. OS-plane work runs in a Linux VM/container (Docker Desktop or Lima). eBPF and
uprobes work there with the right capabilities; hardware trace does not. Hardware trace is
therefore not a foundation, and it isn't needed to be one: the portable thing is the
protocol, not the capture.

## 4. Pipeline

```
 ┌── capture (per runtime, per plane) ──┐   ┌──────── language-agnostic ────────────┐
  stimulus ─► process ─► collectors ─► Execution ─► resolver ─► composer ─► graph/render
  (test /               (OS plane +     (protocol,   (boundary   (fragments,
   probe /               symbol plane)   JSON)        rules)      seams, joins)
   direct call)
```

- **Stimulus**: existing test, generated probe, or direct call. Only a way to *cause*
  execution. Recorded on the `Execution` so probe-derived evidence stays distinguishable.
- **Collectors**: one or more per execution, each tagged `(plane, fidelity)`. They emit
  facts only: calls, substitutions (with what the stand-in *claims* to replace), OS events.
- **Resolver**: classifies each `SubstitutionNode` as internal / external / unresolved by
  ordered deterministic rules (§6). Knows the repo's source roots and nothing else.
- **Composer**: indexes real calls by symbol across executions, expands internal
  boundaries into fragments recursively, and grades each seam by `JoinStrength` (§7).
- **Renderer / graph**: a text tree for the experiments. Persistent storage is *later*.

Only the collectors know about a runtime. A Go or Node collector plugs in to the left of
`Execution` and reuses everything to its right. The layering, stated once:

| Layer | Specific to |
|---|---|
| capture | platform and runtime |
| event/evidence protocol | nothing |
| reconstruction / composition | nothing |
| exploration / probe generation | nothing, above a thin runtime adapter that writes and runs a probe |
| behavioral diffing | nothing |

## 5. Data model

Defined in [`src/diffgenome/model.py`](../src/diffgenome/model.py).

### Observation: the event protocol

| Type | Meaning |
|---|---|
| `SymbolId` | `"<lang>:<qualified name>"`. **The join key for composition.** Both sides of a seam must produce it identically. |
| `Collector` | `name`, `plane`, `fidelity`. Every node cites one. |
| `Execution` | one stimulus on one process: `stimulus` kind + ref, outcome, revision, collectors, nodes |
| `CallNode` | logical call on the symbol plane; `parent` forms the tree; `args` as `(name, shape, digest)` per position; `outcome` (`returned` / `raised:<symbol>` / `unknown`); `result` digest; `thread` |
| `SubstitutionNode` | control left the production symbol space into a stand-in. Keeps three facts apart: `substitute` (what actually executed), `claimed_target` (what production component it stands in for) and `relation` (how the two are related), plus the `mechanism` (mock object / fake / DI binding / interposition / stub) and the member `path` invoked. **Not necessarily a leaf**: a fake or in-memory repository executes code, and that code appears as its children. |
| `OsEventNode` | kernel-visible event (`CONNECT`, `OPEN`, `EXEC`, `SPAWN`, ...) with target and outcome, attributed to the innermost symbol-plane call when possible |

A stand-in's `claimed_target` is a **fact about the artefact** (an autospec's class, a
`patch("pkg.mod.Name")` string, a gomock's interface). Whether that claim is trusted, and
what it maps to, is the resolver's job. Collectors never classify.

`SymbolId` is **provisional**. `<lang>:<qualified name>` is enough for experiment 01 and is
expected to break on source path vs module, defining type vs receiver, overloads,
interfaces vs implementations, closures, generated functions, generics and monorepos. The
rule is that identity disagreements raise `IdentityMismatch`; a composition is never lost
silently.

### Interpretation: always with provenance

| Type | Meaning |
|---|---|
| `BoundaryResolution` | `INTERNAL` / `EXTERNAL` / `UNRESOLVED`, target symbol, and the **rule** that decided it |
| `JoinStrength` | `SYMBOL < ARG_SHAPE < VALUE < STATE`: how a composed seam was matched on *entry*. Join validity is entry × exit: `Evidence.exit` is `same` / `kind` / `unknown`; an exit conflict (different outcome categories, or two different known identities) is unsound at every grade. Result compatibility (did the fragment return what the stand-in returned) is reported on the join attempt, independently of the grade. |
| `Evidence` | `kind`, `site` (the observed node grounding it), `rule` (derived kinds only), `fragment` + `join` + `alternates` (composed only), `probe_derived` |
| `Edge` | caller → callee + one `Evidence`. A symbol pair may have many edges with different evidence. |

`EvidenceKind`, rendered:

| Kind | Rendered | Meaning |
|---|---|---|
| `OBSERVED` | `→` | complete trace, real caller, real callee, same execution |
| `OBSERVED_SAMPLED` | `→?` | sampled collector: callee seen under caller; order and count unknown |
| `COMPOSED` | `⇢` | call reached an internal stand-in; continuation borrowed from `fragment`, graded by `join` |
| `STATIC` | `---→` | statically possible, never executed (*reserved*) |
| `INTERNAL_GAP` | `[gap]` | internal stand-in, no execution of the real target exists yet: probe candidate |
| `EXTERNAL_BOUNDARY` | `[external]` | **semantic** boundary: the stand-in represents code outside the repo |
| `OS_BOUNDARY` | `[os: connect …]` | **physical** boundary: the process tried to leave through the kernel |
| `UNRESOLVED_BOUNDARY` | `[unresolved]` | stand-in we could not classify; reported, never guessed |

Constructor-enforced invariants: composed evidence must have fragment, rule and join;
direct observations (`OBSERVED`, `OBSERVED_SAMPLED`, `OS_BOUNDARY`) may carry no rule,
fragment or join; every derived kind must name its rule.

A precise point about `⇢`: the *call into* the stand-in **was** observed in the seed
execution. Only the continuation is borrowed. So `Evidence.site` always points at a real
observation, even for composed edges.

**Semantic vs physical boundaries are different things** and the model keeps both. A fake
repository or a DI interface is an architectural boundary with no syscall behind it.
`openat()` on a config file is a syscall with no architectural meaning. When both agree
(a stand-in for an HTTP client *and* no `connect` observed) that's corroboration. When they
disagree (no stand-in, but a `connect` attempt) that's a finding: an un-substituted
external dependency, which the sandbox will have refused.

**Reversibility.** A compact "genome" token sequence (`1842 → 993 → 4117`) is an
interning of `SymbolId`s and event kinds for models and storage. It is *later*, and every
token always resolves back to symbol, source location, event and provenance. Interning
never replaces the symbol table.

## 6. Boundary resolution

Ordered rules; the first match decides; the rule name is recorded.

| # | Rule | Condition | Result |
|---|---|---|---|
| R0 | `patch-target` (relation, not a rule) | the stand-in was installed by an interposition mechanism (`patch`) whose saved original *is* the claim; R2–R5 then apply to that claim | — |
| R1 | `no-claim` | stand-in claims nothing (`claimed_target is None`) | `UNRESOLVED` |
| R2 | `claim-in-tests` | claimed target is defined under a test root (a specced fake) | `UNRESOLVED` |
| R3 | `claim-outside-repo` | claimed target defined outside the source roots, or in native/runtime code | `EXTERNAL` |
| R4 | `claim-member` | claimed target in repo and `path` resolves to a definition | `INTERNAL`, target = that definition |
| R5 | `claim-return-chain` | claimed target in repo but `path` crosses a return value | `UNRESOLVED` |

No rule uses names. A claim-less stand-in whose invoked member is called `quote` is *not*
linked to `PricingService.quote`. Weaker rule families come later, each with its own rule
name so they can be filtered: `interposition-target` (patch strings name the replaced
object exactly), `sole-implementation` (interface with exactly one in-repo implementation;
several → report candidates), `injection-annotation` (static type of the parameter the
stand-in was passed into), and `llm-ranked` (a hypothesis, never promoted without
corroboration).

In-repo adapters that wrap external SDKs are **internal**. Their own tests substitute the
SDK, which is where the external boundary really is; if they have no tests, that's a gap.
A true external boundary is never crossed on purpose: we don't un-substitute Stripe, Kafka,
a database or an HTTP service to see what happens, even though the sandbox would block it.
Exploration stops there semantically.

## 7. Composition: the core research problem

```
index: for every passing execution E, for every CallNode n in E:
           fragments[n.symbol] += (E, n)         # a fragment is a subtree, at any depth

expand(E, node, on_path):
    for child in children(E, node):
        CallNode          : emit OBSERVED / OBSERVED_SAMPLED per collector; expand(E, child)
        OsEventNode       : emit OS_BOUNDARY (leaf)
        SubstitutionNode  : resolve ->
            EXTERNAL   : emit EXTERNAL_BOUNDARY (leaf)
            UNRESOLVED : emit UNRESOLVED_BOUNDARY (leaf)
            INTERNAL t :
                if no fragments[t]: emit INTERNAL_GAP (leaf)         # probe candidate
                for (E2, n2) in fragments[t]:
                    if t in on_path: emit COMPOSED to a cycle marker; continue
                    j = grade_seam(child, (E2, n2))                    # JoinStrength
                    emit COMPOSED(site=child, fragment=(E2, n2), join=j)
                    expand(E2, n2, on_path ∪ {t})
```

`same symbol ⇒ compose` is only the floor. Each fragment is a pair (entry state, path), and
composition is sound iff the state at the seam in the seed is compatible with the entry
state of the fragment. The join lattice grades how much of that we checked:

| Join | Checks | Needs from collectors |
|---|---|---|
| `SYMBOL` | same `SymbolId` | nothing more |
| `ARG_SHAPE` | arity and types compatible | bounded arg summaries at substitution sites and call nodes (already in protocol) |
| `VALUE` | equal content digests at every observed position, outcomes known-compatible | bounded digests at seams (implemented; see experiment 02) |
| `STATE` | receiver fields and the module/class state the target reads agree, by bucket (experiment 07) | bounded, value-free state facts on call nodes and seams: `self:type`, first 16 receiver fields, module/class names the code reads. Never whole-process memory, never values. Only consulted once VALUE holds; no common fact ⇒ stays VALUE. |

Fragments are never flattened. Fragments for one target are grouped by **behavior shape**
(symbols, kinds, outcomes, claims and paths of the subtree, not values); each shape is one
branch, expanded once, represented by its best-graded member with the others kept as
`Evidence.alternates`. On Kokoro-FastAPI this took composition from 11,524 to 406 composed
edges with no provenance lost. Recursion is bounded by `on_path` and a depth limit.

A seam with a known conflict (an exit conflict such as returned vs raised or
`returned-error` vs `panic`, an argument-type conflict, or a state conflict) is unsound
and never composed, at any threshold; it is recorded as a rejected join. The lattice is not
metadata. It is the mechanism that stops composed behavior being shown
as stronger than the evidence: a `SYMBOL`-only seam renders and counts differently from an
`ARG_SHAPE` seam, and the north star only counts `ARG_SHAPE` and above. Weak and failed
joins (seam found, no fragment compatible at the required grade) are recorded as
first-class results: they are the queue that targeted probe generation works from.

## 8. Sandbox

Every target repository and every generated probe is untrusted code. Execution happens in
a disposable Linux container with:

- no inherited environment or secrets; an explicit allow-list of variables;
- no mounts of `~/.ssh`, cloud/kube configs, git credentials, the Docker socket;
- **no network egress**: a network namespace with no default route, so `connect` fails
  fast with `ENETUNREACH` and is recorded by the OS-plane collector as `OS_BOUNDARY`
  evidence. Attempts become data; nothing gets through;
- target repo mounted **read-only**; probes written to a copy or worktree in the
  workspace; workspace destroyed after the run;
- CPU, memory, pid, disk and wall-clock limits;
- the OS-plane collector needs `CAP_SYS_PTRACE` (ptrace/strace) or eBPF capabilities; the
  symbol-plane collector needs nothing extra.

This isn't a later hardening step. The OS-plane collector *is* the egress guard's
observation half, so the sandbox and the collector are built together.

The sandbox is a safety net and an observation mechanism, **not an exploration strategy**.
Its block-and-observe behavior is tested with a synthetic canary that we control. An
unexpected egress attempt from target code is a *finding* (an un-substituted external
dependency), never something we provoke.

### Privacy of state facts (experiment 07)

State facts widen what a collector looks at, so their handling is explicit:

- **Fields read.** Receiver: type and the first 16 own fields (`__dict__` / exported struct
  fields / own enumerable properties). Globals (Python only): names in the function's
  `co_names` that resolve in its own module, plus attributes read through an imported module
  or class. Nothing else: no locals, no arguments' object graphs, no closures, no stack.
- **Raw values are temporary.** They are read in the target process by the collector and
  reduced to a bucket in the same call; the bucket is the only thing appended to the node.
  No raw value is serialized, logged, or retained past the `bucket()` call.
- **What is persisted.** `(name, bucket, digest)`. Buckets are one of ~12 coarse classes.
  The digest is non-empty only for `obj:<Type>` and `enum:<member>` facts, and it is a
  digest of the *type or member name*, never of a value.
- **Low-entropy values.** A boolean, a small integer or a short string would be trivially
  reversible from a content digest; that is why state uses buckets (`bool:true`,
  `num:pos`, `str:nonempty`) and not the sha256 digests used for argument values. A secret
  string is `str:nonempty`; a key byte slice is `coll:many`; a token object is `obj:<Type>`.
- **Keyed digests.** Argument-value digests (VALUE rung) are unsalted sha256 over a
  bounded JSON rendering; they are comparable across runs by design, which is also why they
  are never taken of state. If cross-run comparability of argument digests becomes a
  disclosure concern, a per-corpus key can be introduced without changing the protocol
  (the digest is opaque to the composer); this is not done.
- **Stand-ins.** A mock receiver contributes no fields (`obj:stand-in[:spec]` only).

## 9. Deterministic vs AI

| Concern | Who | Why |
|---|---|---|
| Runtime events, ordering, caller attribution | deterministic (collectors) | ground truth |
| Symbol mapping (address/frame → `SymbolId` → source) | deterministic | ELF/DWARF/runtime metadata |
| Whether a syscall occurred; whether a probe executed its target | deterministic | observed |
| Boundary classification when a claim exists | deterministic rules | file location vs source roots |
| Composition, join grading, provenance, rendering | deterministic | data transformation |
| Resolving claim-less / ambiguous stand-ins | *later:* static inference, then LLM as **ranked hypothesis** | tagged with its own rule; never counted as fact |
| Writing generated probes | *later:* LLM-assisted | validity checked deterministically: passes, executes the target (traced), produces no `OS_BOUNDARY` egress |
| Prioritizing dark regions | *later:* heuristic, then LLM | judgement |
| Semantic naming of components, behavioral motifs | *later:* LLM / models over interned sequences | presentation and pattern recognition |

AI proposes; execution establishes facts.

## 10. Risks and things we're actively trying to break

1. **Composition soundness.** Symbol joins over-approximate; the seed keeps running on a
   fabricated return value after the seam. Measured in experiment 04; mitigated by the
   join lattice.
2. **Denominator definition** for the north star (§1).
3. **Claim-less stand-ins and interposition** may dominate real suites; measured in
   experiment 02.
4. **Hand-written fakes** aren't framework objects; they look like real calls into
   `TEST`-origin code. Detecting them as boundaries is open (`TEST`-origin callee reached
   from `REPO`-origin caller is the candidate signal).
5. **Symbol identity drift** between how a collector names a function and how the resolver
   names a claimed target. Silent composition failure; must be asserted, not assumed.
6. **Frameworks between stimulus and code.** `TestClient` runs the app in a portal thread
   behind FastAPI/Starlette/anyio; supertest goes through Express middleware. Caller
   attribution across framework frames, threads and event loops is untested.
7. **Concurrency, async, generators, callbacks, recursion, reflection, dynamic dispatch,
   generated code.** Each is a known way to break a shadow-stack tracer or a symbol join.
   They're on the falsification list for experiment 02, not deferred indefinitely.
8. **Polymorphism**: a claim on an interface yields candidates, not a target.
9. **Probe drift into integration tests**: a probe that passes by under-substituting. The
   OS-plane egress evidence is the deterministic guard.
10. **What counts as "the repository"** in monorepos, vendored and generated code.

## 11. Experiment sequence

Targets are local copies under `~/sample_repos`, always mounted read-only.

| # | Question | Target(s) |
|---|---|---|
| 01 | What is the observability floor per plane, and does composition survive one internal seam with provenance intact? | `fixtures/exp01_shop` (controlled), `demo-orders-api` (real framework, no stand-ins) |
| 02 | Does reconstruction survive less artificial organization, and what breaks it? Resolution rate by rule, gap count, collector failures, the falsification list. | `fastapi-cross-file`, then a larger Python repo |
| 03 | Is the protocol Python-shaped? A second runtime family must emit it unchanged. | `express-api-starter-ts` (Node) |
| 04 | Generated probes: fill `INTERNAL_GAP`s under the sandbox guard; re-compose. | exp01 fixture, `fastapi-cross-file` |
| 05 | Ground truth: compare composed paths with real end-to-end traces on a repo that *can* run whole. Precision/recall of composition; first real north-star number. | `demo-orders-api` (in-process end to end) |
| 06 | Portability stress: compiled language, generated mocks, different runtime model. | `simplebank` (Go, gomock, uretprobe caveat) |
| 07 | Does a bounded, value-free STATE rung change what is accepted where VALUE is vacuous? Exit categories; adversarial ground truth; VALUE-only vs STATE on the same corpus. | `fixtures/exp07_state`, Kokoro and simplebank replays |

Big applications (Immich, Strapi, Flagsmith, GrowthBook) are out until 01–06 hold; they'd
bury the research question under setup problems.

## 12. MVP pipeline (built)

```
repo + diff ─► existing tests traced (confined) ─► Corpus ─► BehavioralGraph
    ─► ChangeSet (diff lines → symbols via the language adapter's AST index)
    ─► Neighborhood (bounded up/down walk) ─► Metrics (provisional)
    ─► ProbeObjectives (gaps, then weak joins, nearest the change)
    ─► ProbeWriter (LLM; replaceable) ─► ProbeRunner (workspace + Seatbelt + egress guard)
    ─► verify (passed, target really ran, no egress, map improved) ─► re-compose ─► report
```

| Module | Layer | Specific to |
|---|---|---|
| `graph.py` | behavioral graph, queries, metrics | nothing |
| `change.py` | diff → ranges → symbols | nothing (mapping via a `SymbolIndex` adapter) |
| `collect/py_symbols.py` | AST symbol index, source extraction | Python |
| `probe.py` | objectives, context, verification, loop | nothing above the source adapter and the pytest command |
| `llm.py` | `ProbeWriter` seam; OpenAI and recorded writers | provider, behind one method |
| `sandbox.py` | workspace, scrubbed env, limits, OS confinement | platform (macOS Seatbelt today; Linux runner later) |
| `report.py`, `mvp.py` | deterministic text/JSON report; one command | nothing |
| `runtime.py` | `RuntimeAdapter` / `SymbolIndex` seam: prepare a workspace, run stimuli, place probes, state conventions | nothing |
| `collect/py_runtime.py`, `collect/node_jest.py`, `collect/go_test.py`, `tools/node-collector/`, `tools/go-collector/` | the three runtime implementations | Python; Node; Go |
| `projection.py`, `ambiguity.py` | behavioral projection of the evidence graph; ambiguous and rejected compositions | nothing |
| `static_types.py` | `factory().member` claims through declared return types (rule `static-return-type`) | nothing above `SymbolIndex.return_type_of` |
| `evaluate.py` | edge precision/recall and seam-level join grading against hidden whole executions | nothing |

AI proposes; execution establishes facts. A probe is accepted only on evidence from its
own trace, and everything it contributes is marked `probe_derived`.

The graph is materialized as `graph.json` (format `diffgenome-graph/1`): every symbol
with origin, location, executing tests and outcomes; every edge with kind, join histogram,
rules, executions, probe flag and its full evidence (site, fragment, alternates); gaps; and
every join attempt including rejected and unsound ones. It loads back without the corpus
for queries (`inspect`) and grading (`evaluate`).

## 13. Deliberately not built

Persistent graph store, genome interning, commit-to-commit diffing, test selection, static
analysis, non-Python collectors, UI, plugin frameworks, learned exploration policy.
