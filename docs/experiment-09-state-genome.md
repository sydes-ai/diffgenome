# Experiment 09: exact mechanics underneath the genome, and state-driven behavior

## Question

If deterministic machinery supplies exact program mechanics and runtime evidence, can the
Behavioral Genome plus an LLM semantic layer reconstruct and predict **state-dependent**
behavior, and not merely summarize guard-driven handlers?

The principle for this pass: *classical analysis reconstructs mechanics; models
reconstruct meaning.* Branch direction, local def-use, control dependence and state deltas
are now established mechanically. The model is asked only for names, predicate
abstraction, relevant state, rules and regimes. Sydes is unchanged.

## Part 1: stable decision-site identity and runtime branch outcomes

**Identity.** A decision site is identified by
`"br:" + sha256(file ":" start line ":" start col ":" end line ":" end col)[:12]`, computed
over the **original** source span of the `if` condition, with 1-based byte columns
(`diffgenome/sites.py`, and `siteID` in the Go instrumenter). Every runtime and every static
front end computes it independently from the original source, so instrumentation cannot
change it: Go reads positions from the original parse before any rewriting.

| runtime | mechanism | outcome recorded |
|---|---|---|
| Python | `sys.monitoring` BRANCH events. The jump instruction's position is mapped to the innermost `if` whose condition contains it; the outcome is whether control enters that if's then-block. Jumps that stay inside the condition (short-circuit operands) are ignored, and non-`if` branches are disabled at their location. | the condition's value, not the jump direction: `if not self.enabled` reports `True` for a disabled processor |
| Go | the instrumenter rewrites `if cond {` to `if dg.Branch("<site>", cond) {` | the condition's value, returned unchanged |
| Node | not implemented: neither experiment needed it | — |

Each observation is `(site, outcome, enclosing call node, seq)`. `seq` orders it against the
calls around it (`Execution.branches`, protocol-additive).

**Mapping to static sites:**

| case | branch observations | mapped exactly to a static site | unmapped because |
|---|---|---|---|
| simplebank (Go) | 547 | 423 | the sites are in closures (`FuncLit`), which the facts pass does not lower |
| Kokoro model manager (Python) | 84 | 69 | the sites are in files outside the lowered module (routers) |

## Part 2: conservative intra-procedural dependence and control

`diffgenome/dependence.py` is language-neutral. It runs over a small structured IR that
front ends produce: `frontends/python_ir.py` via `ast`, and `-facts` in the Go
instrumenter via `go/ast`, from the original tree.

- **Local def-use** by reaching definitions over structured code. Origins are
  `param:account.Balance`, `call:server.validAccount#0`, `global:settings.x`, `const`.
  Anything the analysis cannot follow is `unknown:UNKNOWN_DEPENDENCE:<reason>`; the reasons
  are loop variable, assigned in loop, address passed to a call, and opaque region.
- **Control requirements**: for every call, field store, return and decision, the
  (site, outcome) pairs required to reach it. For structured code this equals transitive
  control dependence. Early-exit guards (`if c { …; return }`) make the rest of the block
  require `c = false`. Loops, exception handlers, `switch`/`select`/`match`, `defer` and
  `go` add an explicit unknown requirement instead of a guess.
- **Decision order**: the pre-order position of every site, and which sites require which.
- **Static write facts**: every field store, with its requirements and value origins.

Examples of what is now established mechanically:

```
checkSufficientBalance: account.Balance < amount   operands ← param:account.Balance, param:amount
createTransfer:        !server.checkSufficientBalance(ctx, fromAccount, req.Amount)
                       fromAccount ← call:server.validAccount#0
                       req.Amount  ← const, UNKNOWN_DEPENDENCE:address-passed-to:ctx.ShouldBindJSON
                       requires: bind-err=F & !valid=F & owner-mismatch=F & !valid=F
server.store.TransferTx requires the five guards above and !checkSufficientBalance=F
_unload_backend_locked: store self._backend ← const   requires `self._backend is None` = F
get_manager:           `ModelManager._instance is None` operand ← global:ModelManager._instance
```

Explicitly `UNKNOWN_DEPENDENCE`: 11 of 306 decision operands in simplebank, mostly a
request field written through `&req` by the JSON binder; none in the model manager. There
are 6 opaque statements in simplebank. There is no interprocedural analysis, and no
alias, heap or dynamic dispatch. A call's arguments are resolved at the call site only.

## Part 3: observed state deltas

The Python collector records the same bounded, value-free state view on exit
(`CallNode.state_after`) as on entry. The Go runtime does the same for the receiver.
The deltas are observed, and they are *not* complete write sets, since nested mutations
through other objects may be invisible. One addition makes settings observable:
attributes read through a global *object* (`settings.model_auto_unload_timeout_seconds`)
are bucketed like those read through modules and classes.

Observed on the model manager: `unload` sets `self._backend` from `obj:stand-in` to
`none`. `generate` on an unloaded manager sets it from `none` to `obj`, which is lazy
re-initialization. `_begin_request` and `_end_request` move `self._active_requests`
from `num:zero` to `num:pos` and back. `_schedule_idle_unload_timer_locked` sets
`self._idle_unload_task` from `none` to `obj:Task` only when enabled and idle. The timer
unloads the backend later.

## Part 4: genome and checker, minimally extended

The schema (`genome.py`) gains:
- `Decision.site`;
- `Variable.observed_as`, binding a variable to an observed fact as `is_set`, `sign` or `bool`;
- machine-readable `Transition` (`entity`, `when`, `sets`);
- `Procedure` (ordered `call:` / `T:` / `D:` steps);
- `Branch.steps`;
- evidence kinds `branch`, `control`, `dataflow`, `delta` and `store`.

`genome_state.py` holds the checker and the sequence predictor. The checker remains the
only authority on status. Rules added in this pass, most of them forced by failures found
while running it:

| rule | why it exists |
|---|---|
| A decision is verified only if it is anchored at a site, both outcomes are observed, its claimed consequences are consistent with the site's static control facts, no observed branch contradicts it, it does not share the site with another decision, and its predicate agrees with the observed outcomes | Experiment 08's D3 was first "verified" at a mislinked site; the agreement check caught it |
| **Local agreement**: at each observed evaluation, the predicate on the call's observed entry state (plus execution-constant globals, minus fields the function stores before the site) must give the observed outcome. A local contradiction **rejects** a decision whose site the proposal named | a whole-genome replay made one wrong decision reject a correct one (control c2); local agreement attributes blame to one decision |
| Replay or stated-fact disagreement only blocks verification | it is not attributable to a single decision |
| A site linked by the checker's citation heuristic never leads to rejection | the link is the checker's inference, not the model's claim |
| A transition placed in a procedure is checked where the procedure applies it: the entity's procedure is run from the call's observed entry state | "timer armed" happens only after the guard lets execution through, and was wrongly rejected as unconditional |
| A fabricated site id makes the decision a hypothesis | control c4 |
| Executions outside the genome's sequential scope (concurrency) are excluded from agreement and said so | local agreement assumes no interleaving across `await`; the concurrent test broke it |
| Unknown or unestablished semantics stop prediction (inherited from Experiment 08) | — |

## Part 5: path conditions

An execution's **branch vector** over the genome's sites is recorded as an observed fact
(`path_condition()`), for example `ensure_backend:self._backend=T, generate:volume=F,
_schedule:guard=F, …`, with each site's source predicate attached. Regimes are
equivalence classes of branch vectors (`regimes()`). A *symbolic* path condition exists only
where the genome supplies a machine-readable predicate over bound variables. No symbolic
completeness is claimed.

## Evaluation of the substrate

1. **How are branch sites identified?** By a hash of the file and the original source span
   of the condition, computed independently at runtime and statically.
2. **Stable across instrumentation?** Yes, by construction. Go computes ids before rewriting.
   Python observes without rewriting.
3. **Exact mapping to source sites?** Yes, for every lowered function: 423 of 547 (Go) and
   69 of 84 (Python). The unmapped observations are in closures and in files that were not
   lowered.
4. **Deterministic local dependencies**: parameters, locals, call results with position,
   field reads, and globals, resolved to origins for every decision operand, call argument
   and field store.
5. **`UNKNOWN_DEPENDENCE`**: loop variables, values assigned in loops, locals whose address
   is passed to a call, opaque regions, and complex expressions.
6. **Control and order established mechanically**: each outcome's controlled calls and
   stores, early-exit guards, and the order and nesting of decisions within a function.
   Order across functions is not established.
7. **Deltas observed**: the manager lifecycle above, and `Processor.seen` in the Experiment 07
   fixture.
8. **Experiment 08 items under the stronger substrate** (its proposals unchanged, re-checked):

| decision | Experiment 08 | now | why |
|---|---|---|---|
| D8 balance guard | verified (helper's decoded return) | **verified at `account.Balance < amount` itself** | the relational predicate agrees with the observed outcome in 3 tests |
| D5 ownership | supported | **verified** | its site is observed both ways; agrees in 6 tests |
| D9 TransferTx error | supported | **verified** | agrees in 2 tests |
| D1 currency binding | verified | supported | shares the binding site with D2: the observable outcome decides only "binding failed", not why |
| D3 account not found | supported | supported (refused) | its citation links it to `errors.Is(err, ErrRecordNotFound)`, where its predicate disagrees with what executed (`GetAccountError`) |
| D4 / D7 currency, from / to | supported | supported | one context-insensitive site serves both calls of `validAccount`; per-call-context decisions need call-site context |
| D0 auth, D6 to-account lookup | supported | supported | D0's site is in a closure (not lowered); D6 has no unique cited site |

## Experiment 09: the ModelManager lifecycle (Kokoro-FastAPI)

**Case.** `ModelManager` loads, unloads and lazily re-initializes a backend, counts active
requests, and schedules an idle-unload timer whose arming depends on that count, the backend
and a setting. The timer later unloads the backend. This is behavior of the form
`S0 → call → S1 → later call takes a different path`, not a guard sequence. There are 14
unit tests: 10 shown, 4 withheld from both the model and the checker. The concurrency test
is shown but not scored.

**Method (same as Experiment 08).** The bundle is deterministic: 1,017 lines, digest
`3a1ae9e7a4b03316`. It holds the mechanics, chronological event logs with branch outcomes
and state deltas, the source, and the test source. A fresh Opus instance saw only the
bundle; one call, about 106k subagent tokens. **Statuses were established from the shown
tests only**, and the withheld tests were then predicted cold. This is stricter than
Experiment 08, where statuses used every execution.

**Genome.**

| element | count | verified | notes |
|---|---|---|---|
| variables (5 bound to observed state) | 9 | – | `backend_loaded`, `active_requests`, `last_used_set`, `timer_pending`, `unload_timeout` |
| decisions (all anchored at given sites) | 16 | 4: fast-path backend check, timer cancel, scheduler guard, CUDA check in `unload` | 12 supported, most because only one outcome is observed in the shown tests |
| transitions | 10 | 7: init, begin, end, cancel-clear, schedule-arm, load-touch, unload | `initialize` is mocked in every test; `unload_noop` sets only an unbound local; `unload_all` is never called |
| procedures | 17 | – | composition, including `hold`'s bracketing of the `generate` body |
| rules / regimes | 5 / 2 | – | auto-unload on versus off |

**Prediction.** From scenario to procedures, decisions and transitions, then to the
predicted decision outcomes at the genome's sites (in order) and the predicted final bound
state. Both are compared exactly with what executed.

| | exact |
|---|---|
| scored tests (13) | **13 / 13** |
| withheld from the model and the checker (4) | **4 / 4** |
| same genome, every transition removed (stateless ablation) | **3 / 13** |

A concrete example of state doing the work, `test_generate_schedules_idle_unload_when_enabled`:

```
with transitions:  … _end_request sets last_used_set := true, schedule arms the timer;
                   timer fires: guard `unload_timeout <= 0 || !backend_loaded || active_requests > 0 || !last_used_set` = F
                   → unload → backend_loaded = false   (matches what executed)
stateless:         the same calls, but last_used_set is still false when the timer fires
                   → guard = T → skip → backend_loaded stays true   (wrong)
```

**Controls** (seeded proposals, same pipeline). None produced a determinate wrong prediction.

| control | caught as | exact | indeterminate | determinate wrong |
|---|---|---|---|---|
| c1 wrong transition (`unload` leaves the backend loaded) | transition **rejected** by observed deltas | 7 | 6 | 0 |
| c2 inverted scheduler guard | decision **rejected** at its own site from observed state; the correct cancel decision is only left unverified | 7 | 6 | 0 |
| c3 missing transition (`_begin_request` does not count) | prediction **indeterminate** wherever it is needed | 9 | 4 | 0 |
| c4 fabricated site id | decision demoted to **hypothesis** | 9 | 4 | 0 |

## Answers

1. **Which state variables matter?** Backend loaded, active request count, last-used set,
   timer pending, and the auto-unload timeout setting. Every one is bound to an observed fact.
2. **Which transitions and effects were observed?** Construction; begin request (+1); end
   request (−1, touch); cancel clears the timer; scheduling arms it; load touches; unload
   clears the backend. Seven are verified from observed deltas where the procedure applies them.
3. **Can the genome predict held-out behavior?** Yes: 4 of 4 exact, with statuses established
   without them.
4. **Does it distinguish behavior a guard sequence cannot represent?** Yes. The stateless
   ablation, the same decisions without state change, falls to 3 of 13. A later decision
   (the timer's guard) depends on state set by an earlier call (`_end_request`).
5. **Verified versus supported?** 4 decisions and 7 transitions are verified. The rest are
   supported: mostly single-outcome sites in the shown tests, plus mocked or unexecuted
   entities.
6. **Are seeded bad proposals caught?** Yes, all four, and no control produced a confident
   wrong prediction.
7. **Indeterminate when an essential transition is unknown?** Yes: c3 makes exactly the 4
   dependent predictions indeterminate, and none wrong.
8. **Did Opus add meaning beyond the dependence and control graph?** Yes, in places the
   mechanics cannot reach:
   - **Interprocedural predicate abstraction**: `not self._auto_unload_enabled()` becomes
     `unload_timeout <= 0`, through the body of `_auto_unload_enabled`.
   - **The context-manager protocol**: `hold()` brackets the `generate` body with
     begin/end, which the intra-procedural `with` facts do not say.
   - **Reading test setup into initial state**, and `await asyncio.sleep` as the timer firing.
   - **Choosing bindings and abstraction kinds**, and grouping regimes.
   - **Precise unknowns**: the cancel predicate's missing clauses, and concurrency.

   The branch outcomes, control requirements, def-use and deltas it was given, it used
   without contradicting.
9. **More generative than Experiment 08?** Yes. Experiment 08 predicted paths through one
   handler from input facts. This genome predicts sequences of calls through a component,
   carrying state from call to call, including a timer firing later. The price is size: 16
   decisions, 10 transitions and 17 procedures for 14 tests. Over the genome's sites the
   tests fall into 13 path-condition classes, so this component's tests are nearly all
   distinct regimes. The gain is generativity, not a smaller class count.
10. **Does this strengthen or weaken the hypothesis?** It strengthens it, with the scope
    stated plainly. With exact mechanics underneath, a bounded model produced a state
    genome that predicts held-out, state-dependent sequences exactly, while the checker
    kept wrong semantics out. Three limits showed up:
    - **Concurrency**: interleaving across `await` breaks both sequential prediction and
      local agreement.
    - **Context-insensitive sites**: one site in a function called twice cannot verify
      per-call decisions.
    - **Mocked entities**: their transitions can only be inferred through the caller's deltas.

## Flaws found in my own tooling during this pass (all fixed, and tested where cheap)

- Verification of Experiment 08's D3 at a mislinked site. Fixed by semantic agreement.
- Reachability that counted calls before the site. Fixed by position-aware reachability.
- Unconditional-transition semantics that contradicted procedural placement. Fixed by
  procedural transition checks.
- Boolean literals evaluating as unknown variables.
- Whole-genome replay blaming a correct decision. Fixed by local agreement.
- Local agreement assuming no interleaving. Fixed by stating the scope and excluding
  concurrent executions.
- A tree-grouped event log that misordered async calls. Fixed with a chronological log.

## Deferred, as instructed

Sydes, Java/Rust, the OS plane, a graph database, UI, benchmarks, model training,
interprocedural dataflow, symbolic execution, and an agentic query loop. Also noted for
later: lowering closures (Go `FuncLit`), call-site context for sites, and Node branch
recording.
