# Design (Step 2): the smallest extension of the Behavioral Genome that survives Case A

Status: **design only**. No code was changed for this document. It is written against commit
8c1cbf2, which includes the Step 1 repairs.

Evidence used:
- Experiment 10 Case A, Baserow #6069 (`docs/experiment-10-stress-baserow.md`, traces at
  head and base);
- Experiments 08 and 09;
- the real diff of upstream simplebank #103, *add role-based access control*. Its commit
  2e2094e has parent 6e26798, which is Case B's base. It was read, not run. The fork's head
  9a53ee3 is not in the local clone, so the reading assumes the fork reproduces #103 faithfully.

## 1. Problem statement

After Step 1, Case A is fully observed and fully anchored:

| measure | result |
|---|---|
| change branches mapped | 180/180 |
| opaque statements | 0 |
| decisions anchored | 7/7 |
| wrongful rejections | 0 |
| verified decisions | 0 |
| held-out predictions | all indeterminate |

Most importantly, control **c2 (the pre-change semantics) cannot be told apart from the real
genome by any machine check.**

The change is not "if X then call Y". Its behavior runs as a chain:

1. a set of entities;
2. a dependency relation among them;
3. an order derived from that relation;
4. iteration that respects the order;
5. a later outcome that depends on whether the order was right.

The genome can already state each local branch correctly (7/7 sites locally correct in
Experiment 10). It cannot state the relation, the order, the iteration, or the outcome. So the
genome that says "the implied dependency exists" and the one that says "it does not" make the
same checkable claims.

## 2. Why the current IR fails on Case A after Step 1

| gap | consequence in Case A |
|---|---|
| Variables are scalars (bool/int) bound only to **receiver/global state facts** (`self.x`, `global.y`) | The proposer had to squeeze "this reference implies a dependency on the linked primary" into one boolean, `implied_primary_dep`. Nothing observed binds it. The runtime *does* record the hook's result, but that is a call boundary, not receiver state, so the checker cannot see it. **c2 flips that boolean and nothing contradicts it.** |
| No relation-valued state | Which field depends on which, and through which link, has no representation. Identity is lost: "a dependency" instead of "consumer depends on producer". |
| No derived order | Nothing can say "producer before consumer", so nothing can be checked against the order the importer actually ran. |
| No iteration | Per-field behavior had to be flattened into one call list. The proposer mis-nested it, every replay stopped, and nothing verified (F8, F15). Repeated evaluations of one site cannot be tied to the item they belong to. |
| No outcome | "`import_tables_serialized` raises `DataError`" cannot be predicted. Only branch vectors and bound state can, and neither differs between the real genome and c2 at any covered site. |

Step 1 cannot fix this by patching the checker further: nothing in the genome makes a claim
that c2 contradicts.

## 3. Candidate abstractions considered

| candidate | what it adds |
|---|---|
| A. Boundary bindings | bind a variable to an identity-level fact at a call boundary (argument or result): is it set, is it equal to another value, did a step change it. **No new object** |
| B. Relation as a new top-level genome object | a first-class `Relation` beside Variable and Decision |
| B′. Relation as a *kind of Variable* | a variable whose value is a finite set of tuples of opaque identities |
| C. Order as its own object: rank, levels or a topological order | a separate derived-order construct |
| C′. Order as a *derived relation*: one derivation mechanism with transitive closure | order expressed through the same derivation as any other derived relation |
| D. General loops: `while`, `break`, accumulators | full iteration constructs |
| D′. `for_each` as a procedure step | over a relation or collection variable, with an optional order constraint and a body of steps |
| E. Causal links: outcome X was caused by decision Y | explicit cause records |
| E′. Outcome as a predicted *exit category* | an exit category of an entity whose episode contains the cause |
| F. Test pass/fail as the phenotype | the test result itself is the predicted behavior |

## 4. Rejected designs, and why

- **B, Relation as a new top-level object.** It would duplicate everything a Variable already
  has: `derived_by`, `evidence`, `status`, `observed_as`, `definition`. It would also invite a
  table/database abstraction. Relation-valued state is state, so B′ is chosen.
- **C, rank or levels as a primitive.** Checking "producer before consumer" needs only a
  precedence relation. Rank is derivable (the longest path) if a scenario ever needs exact
  grouping. The program leaves order *within a level* unspecified (set iteration), so exact
  rank predictions would over-claim. Rank is rejected as a primitive; precedence is a derived
  relation.
- **A general graph query language** (paths, aggregation, negation in derivations). Case A
  needs join and transitive closure, nothing more. Negation appears only in *checks*
  (subset, empty, exclusion), never in derivations. That keeps derivation monotone,
  terminating and deterministic.
- **D, general loops.** Loops that compute a predicate do not need iteration in the genome.
  The RBAC helper `hasPermission` loops over allowed roles to decide membership, and that is
  abstracted as `role in {…}`. Iteration is needed only when **per-item effects** occur and
  their presence or order matters. Baserow defers or imports each field; RBAC's loop has no
  effects.
- **E, causal links.** Baserow's DataError surfaces two phases after the ordering decision, but
  both lie inside one call episode, `import_tables_serialized`. Attaching the outcome to *that*
  entity and conditioning it on the order observed within its episode is enough. A causal-link
  primitive would need causal evidence the collector cannot provide.
- **F, test pass/fail as the phenotype.** Rejected, as the brief says. A test's result mixes
  assertions with behavior. Outcomes are read from the entity's own observed call outcome.
- **Variables with per-instance names**, such as `consumer_dep_on_childid`. This is what the
  proposer effectively did. It does not generalize across tests, and the identities do not
  match anything observed.

## 5. Proposed minimal schema

All additions are optional and additive. Existing Experiment 08 and 09 genomes stay valid
unchanged. Every new element keeps `derived_by`, `evidence[]` and `status`, and the checker
alone assigns status.

### 5.1 Boundary bindings (extends `Variable.observed_as`)

Today `observed_as` binds a variable to a receiver or global state fact. It gains call-boundary
facts that the collector **already records** as argument and result shapes and digests:

```json
"observed_as": {"at": {"entity": "<function>", "point": "arg:<name>" | "result"},
                "kind": "is_set" | "changed_from:arg:<name>" | "equals:<other point>" | "size" | "bool" | "sign"}
```

The kinds are defined as follows:

| kind | meaning | derived from |
|---|---|---|
| `is_set` | the value is not null or none | the recorded shape type |
| `changed_from` | the step's output differs from its input | digest inequality |
| `size` | the collection's size | the shape, e.g. `set[2]` |
| `bool`, `sign` | as today | small, decodable digests |

This alone makes c2 checkable (section 10). It needs no collector change.

### 5.2 Relation-valued variables (`Variable.kind = "relation"`)

```json
{"id": "R_declared", "kind": "relation", "name": "declared_dep",
 "columns": ["item", "needs", "via"],
 "observed_as": {"at": {"entity": "…add_deferred…", "point": "arg:field_dependencies"},
                 "key": {"item": "arg:field_name"}, "fidelity": "structure" | "identity" | "shape"},
 "definition": null | "<derivation, 5.3>",
 "evidence": […], "derived_by": "llm:…", "status": "…"}
```

- **Members are opaque identities, never raw values.** An identity is the collector's stable
  digest of a scalar or string element. Column names are instance-level labels, not types.
  There is no type system: two columns are comparable because their members come from the same
  digest domain.
- **Set semantics.** There are no duplicates, and multiplicity is not modeled. If multiplicity
  matters, it is an iteration property (5.4).
- **Observation fidelity**, from weakest to strongest:

  | level | name | the observation is | available |
  |---|---|---|---|
  | F0 | `identity` | only a digest of the whole value | today |
  | F1 | `shape` | a size | today |
  | F2 | `structure` | a set of tuples of member digests | needs a collector change (section 11) |

  A capture carries `complete: true|false`. A truncated capture supports only lower-bound
  claims, "contains", never "excludes".
- **Partial relations.** A relation whose F2 capture is missing or incomplete in an execution
  is `UNKNOWN` there. Claims needing its complement become indeterminate there. They are never
  assumed false.

### 5.3 Derivation, one mechanism for derived relations and order

A `definition` on a relation variable is a set of positive rules over relations:

```
R(x, y) :- A(x, z), B(z, y)      # join; several rules for R = union
R = closure(S)                   # transitive closure
R = inverse(S)                   # swap columns of a binary relation
```

That is all: no negation, no aggregation, no arithmetic.
- **Order** is a derived binary relation. For example, `precedes = closure(depends)` with
  columns `(before, after)`.
- **`rank`** is not provided.
- **Checks** usable in predicates and rule conditions:

  | check | reads |
  |---|---|
  | `(a, b) in R` | membership |
  | `R ⊆ S` | subset |
  | `empty(R)` | emptiness |
  | `respects(iteration, R)` | an iteration against an order |

- **Scalars** keep today's predicate language, plus membership in a literal set, `x in {v1, v2}`,
  which Case B needs (6.4).

### 5.4 Iteration, a procedure step

```json
{"for_each": {"over": "<relation or collection variable>", "as": "<binding>",
              "site": "<loop site id>", "respecting": "<derived order relation>" | null,
              "steps": ["D:…", "T:…", "call:…"]}}
```

- The body runs once per element. Body decisions read per-element facts: projections of
  relations on the binding, e.g. `(as, _, via) in R_refs`.
- Per-iteration branch outcomes are keyed by `(site, element identity)`.
- `respecting: R` claims every observed iteration order is a linear extension of R.
- An unknown element count makes body predictions *per-element* claims (∀ observed element),
  not sequence claims.

This intentionally excludes `while`, `break`, accumulators, nesting beyond the body's own
steps, and loops that only compute a predicate. Those use quantifier or membership predicates.

**Episode scoping becomes exact.** Step 1's heuristic episode, "until the next evaluation of the
same site, or until control leaves the loop", becomes *one iteration's element*. That is the
real boundary, and it holds wherever iteration events exist.

### 5.5 Outcome, a predicted exit category of an entity

```json
"outcome": {"entity": "<function>", "is": "returned" | "returned_error:<kind>" | "raised:<kind>" | "panic:<kind>" | "cancelled"}
```

- `completed` is `returned` with no error, not a separate value.
- `<kind>` is the runtime's own type name, instance-level: e.g. `django.db.utils.DataError`,
  `*status.Error`. The core knows only the categories, which already exist in the collector's
  exit taxonomy: `CallNode.outcome` in Python, and Go's returned-error and panic categories
  from Experiment 07.
- An outcome may appear in:
  - `Branch.outcome`: the deciding function exits this way;
  - `Procedure.outcome`: the entity exits this way when its steps complete;
  - `Rule.consequences`: `{"outcome": …}` under a condition, which may involve relations,
    order and iteration.
- **Distance.** A rule's outcome may name an entity *enclosing* the cause, such as the entry
  whose episode contains the ordering. That is how "two phases later" is expressed, without a
  causal link.

### 5.6 New evidence reference kinds

| kind | fields | checks |
|---|---|---|
| `boundary` | entity, point, test, kind, value | a boundary fact in one execution |
| `relation` | variable, test, claim (`contains`/`excludes`/`equals`/`size`/`changed`/`unchanged`), tuple? | a relation observation at its binding |
| `iteration` | site, test, element?, position? | an observed iteration event |
| `outcome` | entity, test, is | the entity's observed exit category in that execution |

## 6. Examples

### 6.1 Experiment 08: simplebank balance guard (unchanged; Outcome optional)

```json
{"variables": [{"id": "V_amt", "name": "request.amount", "origin": "input"},
               {"id": "V_bal", "name": "from_account.balance", "origin": "input"}],
 "decisions": [{"id": "D8", "entity": "Server.checkSufficientBalance", "site": "br:4488ad242266",
                "predicate": "from_account.balance < request.amount",
                "true_branch": {"stops": true, "absent": ["store.TransferTx"],
                                "outcome": {"entity": "Server.createTransfer", "is": "returned"}},
                "false_branch": {"calls": ["store.TransferTx"]}}]}
```

The handler writes a status and returns, so its outcome is `returned`. The HTTP code is a value,
not an exit category. The optional outcome adds nothing here beyond today's `stops`/`absent`.
No relation, iteration or boundary binding is needed. **Experiment 08 does not get more
complicated.**

### 6.2 Experiment 09: Kokoro lifecycle (unchanged)

```json
{"variables": [{"id": "V1", "name": "backend_loaded", "observed_as": {"fact": "self._backend", "kind": "is_set"}},
               {"id": "V2", "name": "active_requests", "observed_as": {"fact": "self._active_requests", "kind": "sign"}}],
 "transitions": [{"id": "T_unload", "entity": "ModelManager.unload", "sets": {"backend_loaded": "false"}}],
 "procedures": [{"id": "P_idle", "entity": "ModelManager._idle_unload_after", "steps": ["D:D_guard", "T:T_unload"]}]}
```

Everything is scalar state with transitions, exactly as today. **No new primitive is used.**

### 6.3 Experiment 10A: Baserow relation and order

Identities are digests of the importer's temporary keys and of field names.

```json
{"variables": [
  {"id": "R_refs", "kind": "relation", "name": "references", "columns": ["item", "ref", "via"],
   "observed_as": {"at": {"entity": "…get_field_depdendencies_before_import_serialized", "point": "result"},
                   "key": {"item": "arg:serialized_field"}, "fidelity": "structure"}},
  {"id": "R_hook", "kind": "relation", "name": "implied_by_reference", "columns": ["ref", "target", "via"],
   "observed_as": {"at": {"entity": "…get_import_dependency_when_referenced", "point": "result"},
                   "key": {"ref": "arg:reference_name"}, "fidelity": "structure"}},
  {"id": "R_declared", "kind": "relation", "name": "declared", "columns": ["item", "needs", "via"],
   "observed_as": {"at": {"entity": "…DeferredFieldImporter.add_deferred_field_import", "point": "arg:field_dependencies"},
                   "key": {"item": "arg:field_name"}, "fidelity": "structure"},
   "definition": "declared(i,t,v) :- references(i,r,v2), implied_by_reference(r,t,v). declared(i,r,v) :- references(i,r,v), not_expanded(i,r,v)"},
  {"id": "R_prec", "kind": "relation", "name": "precedes", "columns": ["before", "after"],
   "definition": "precedes = closure(inverse(declared_pairs))"},
  {"id": "R_needs", "kind": "relation", "name": "reads_from", "columns": ["consumer", "producer"],
   "definition": "reads_from(c,p) :- references(c,l,_), link_target_primary(l,p)"}],
 "procedures": [{"id": "P_run", "entity": "DeferredFieldImporter.run_deferred_field_imports",
   "steps": [{"for_each": {"over": "deferred_items", "as": "f", "site": "loop:…", "respecting": "precedes",
                           "steps": ["call:_import_field_serialized"]}}]}],
 "rules": [{"id": "O1", "name": "a consumer processed before a producer it reads from fails later",
   "condition": "exists (c,p) in reads_from: position(c) < position(p) in iteration(P_run)",
   "consequences": [{"outcome": {"entity": "DatabaseApplicationType.import_tables_serialized",
                                 "is": "raised:django.db.utils.DataError"}}],
   "otherwise": [{"outcome": {"entity": "DatabaseApplicationType.import_tables_serialized", "is": "returned"}}]}]}
```

The first `declared` rule is written loosely, and `not_expanded` is a derived helper relation.
A strict version keeps derivations positive: "declared = expanded ∪ unexpanded" is written as
two positive rules over the hook's `(ref → target)` pairs and a `passthrough` relation that the
hook's *null* results populate. The exact normal form is an implementation detail. The design
point is that negation does not enter derivations.

The per-field decisions at the link-row sites and `not deps` keep their existing form, with
body facts now read from relations. So the site outcomes Experiment 10 already got right
remain the same claims.

### 6.4 Case B conceptually: simplebank RBAC (#103 as written)

The real code:
- a **scalar** role on the user (`users.role`, default `depositor`);
- the role copied into the token payload at login and read back from the token on a later
  request;
- **one call site** that passes a literal allowed set `{banker, depositor}` to
  `authorizeUser`;
- a membership loop, `hasPermission`;
- an ownership rule: `role != banker && username != req.username` means permission denied.

The natural genome:

```json
{"variables": [
  {"id": "V_role", "name": "principal.role",
   "observed_as": {"at": {"entity": "Server.authorizeUser", "point": "result"}, "kind": "field:Role"}},
  {"id": "V_self", "name": "is_self", "definition": "principal.username == request.username"}],
 "decisions": [
  {"id": "D_allowed", "entity": "Server.authorizeUser", "site": "br:…(!hasPermission)",
   "predicate": "!(principal.role in {banker, depositor})",
   "true_branch": {"stops": true, "outcome": {"entity": "Server.authorizeUser", "is": "returned_error:*errors.errorString"}}},
  {"id": "D_owner", "entity": "Server.UpdateUser", "site": "br:…",
   "predicate": "principal.role != banker && !is_self",
   "true_branch": {"stops": true, "outcome": {"entity": "Server.UpdateUser", "is": "returned_error:*status.Error"}}}],
 "transitions": [{"id": "T_issue", "entity": "Server.LoginUser", "sets": {"token.role": "user.role"}}]}
```

A first-class relation would look like this:

```
role_assignment(principal, role)
role_permission(role, action)
authorized(p, a) :- role_assignment(p, r), role_permission(r, a)
```

It is appropriate only when the code holds *many-to-many or data-driven* assignments or
permissions, such as a table of roles per user or permissions per endpoint looked up at
runtime, or when several call sites share a helper with different sets.

**#103 has none of these**: one role per principal, and one literal set at one call site. Forcing
relations here would add machinery the evidence cannot check. The design passes this test by
*not* requiring it. It also means **Case B does not exercise the relation design** (section 14).

## 7. Evidence and provenance model

- **Where evidence comes from:**
  - relation content comes from the collector at F0, F1 or F2, at bindings named by the
    mechanics (the change's functions and the frontier);
  - static relation tuples come from source literals and constant tables (e.g. the literal role
    set);
  - iteration events come from the collector, as a loop site with an element identity and a
    position;
  - outcomes come from the observed exit category of the named entity's call.
- **Per-tuple provenance.** Each observed tuple carries (execution, point, fidelity, complete).
  Each derived tuple carries its rule and the provenance of its inputs, the minimum of their
  statuses. Model-proposed tuples carry `derived_by: llm:…` and their evidence.
- **Revision.** Observations are per revision. Relations compare across revisions only through
  identities, which are stable across base and head runs of one analysis. Site ids stay
  revision-local, so iteration sites need the base↔head site correspondence noted in
  Experiment 10 (F6) before cross-revision order claims can be made.
- **Privacy.** Members are digests, never raw values. Structured capture is opt-in per binding,
  bounded (section 11), and limited to value classes whose digest is safe to keep. The known
  risk is below.

## 8. Deterministic versus model responsibilities

| deterministic (mechanics, collector, checker) | model (proposer) |
|---|---|
| observed relation contents at bindings (F0/F1/F2), static literal sets | *which* boundaries carry meaning, and the column meaning (item, needs, via) |
| evaluation of derivations (join, closure), and checks (subset, respects) | the derivation rules, e.g. "a reference through a link implies the linked primary" |
| iteration events, and per-item keying of branch outcomes | which loop is behaviorally relevant, and what the order *should* respect |
| observed exit categories | outcome rules: which condition leads to which exit, and at which enclosing entity |
| status of every claim | nothing about status |

- **The model never supplies relation contents.** It supplies rules and bindings, and contents
  come from observation or derivation.
- **A semantic relation stays semantic.** A relation that is *only* semantic, like `reads_from`
  (what the consumer truly needs), can be derived from observed relations by a model rule. That
  keeps it checkable. It cannot be verified by direct observation unless the collector ever sees
  read-after-write between iterations, which is not proposed.

## 9. Verification and status rules (conservative)

`observed_fact` and `static_fact` are facts produced by collector/static scans, as today.
`hypothesis`, `supported`, `verified` and `rejected` are assigned to model proposals.

| primitive | observed_fact | static_fact | supported | verified | rejected |
|---|---|---|---|---|---|
| boundary binding | a shape or digest fact at the point in an execution | — | the binding cites real points, and every cited ref checks out | the variable's predicted value at the point equals the observed value in every execution that reaches it, **and both values (e.g. set and unset) occur** | a predicted value is decidable and differs from the observed value at the point |
| relation tuple | captured at F2, complete or partial, in an execution | from a literal or constant in source | derived by a supported rule from observed/static inputs | derived by a *verified* rule from observed/static inputs | — (tuples are not proposed alone) |
| derivation rule (`definition`) | — | — | its output is consistent with every observation of its binding (subset-consistent for partial captures) | its output **equals** every **complete** observation of its binding, in ≥ 2 executions, including one where the rule adds a tuple its inputs lack (non-vacuous) | its output excludes an observed tuple, or includes one a complete capture excludes; at F0, it predicts unchanged where the digest changed, or the reverse |
| order (`precedes` = closure of R) | — | — | the input relation is supported | the input relation is verified. Closure itself is deterministic and needs no verification | never directly: its input is rejected instead |
| iteration `respecting R` | iteration events with element identities | — | no observed violation, but vacuous (no pair of R iterated together) or with elements of unknown identity | ≥ 1 execution in which a pair (a, b) of R is iterated with b after a, and no execution violates R | an observed iteration places b before a for (a, b) in R |
| outcome in a branch or procedure | the entity's exit category in an execution | — | cited refs check out | predicted equals observed in every execution reaching the branch, with the branch observed both ways | predicted differs from observed where the branch was taken |
| outcome rule | — | — | every condition decidable from facts gives the observed outcome, but the condition uses a *supported* (model) relation | as supported, but the condition is decidable **from observed/static facts and verified rules only**, and both the condition and its negation occur | a decidable condition predicts an exit that differs from the observed one |

Everything else keeps today's rules. Unknown or unestablished items that a prediction needs
stop it as indeterminate.

## 10. How c2 becomes mechanically distinguishable

c2 keeps the real genome's structure but says the reference implies nothing: the hook's
result is unset, and `declared` equals `references`. None of the checks below uses a test's
pass/fail, Baserow-specific logic in the core, or model prose.

**Layer 1: boundary bindings only (5.1). No collector change. Works on today's traces.**

| boundary fact | observed at head | real genome predicts | c2 predicts |
|---|---|---|---|
| the link-row hook's result (`LinkRowFieldType.get_import_dependency_when_referenced`) | a tuple, `is_set = true`: 3 calls in the shown tests (implicit ×2, explicit ×1) | set | unset → **contradicted, rejected** |
| the default hook's result (`FieldType.get_import_dependency_when_referenced`), formula-dependency test | `NoneType`: `is_set = false` | unset | unset |
| the expansion's output (`_expand_implied_import_dependencies`) versus its input `field_deps` | changed on the 2 implicit-test calls (#3241eb → #8b5219, #0d70db → #c2703a) and the 1 explicit-test call (#0d70db → #c2703a) | changed on exactly those calls | unchanged → **contradicted, rejected** |
| the same, on the other 23 calls in the shown tests | unchanged | unchanged | unchanged, so no discrimination there, as expected |

The real genome's binding would be verified non-vacuously: set and unset hook results both occur
in the shown tests, and every prediction agrees. The withheld tests give the same pattern: set
twice and changed twice in each.

**Layer 2: relations and order (5.2 to 5.4), with F2 capture and iteration events.**
- `declared` at the importer boundary contains `(ChildId, LinkedChildren)` for the consumer at
  head. c2's derivation excludes it, and a complete capture shows it, so the rule is rejected.
- `precedes` then contains ChildId → consumer. Head's iteration events show ChildId before the
  consumer, so `respecting precedes` is verified non-vacuously.
- Under c2, `precedes` lacks that pair. Its `respecting` claim is vacuous there: not wrong,
  and not verified.

**Layer 3: outcome.**
- Rule O1 predicts `returned` at head, because the order is respected, and
  `raised:…DataError` at base, where the iteration events put the consumer first. Both are
  checked against the observed exit of `import_tables_serialized`.
- Under c2, the head order is unconstrained, so O1's condition is not decidable from c2's
  relations and its head prediction is indeterminate. c2 cannot claim `returned` at head
  without an order that its own relation does not imply.

**What is not claimed.**
- **O1 stays `supported`, not `verified`.** Its condition uses `reads_from`, a semantic
  relation derived by a model rule. The outcome agreement across base and head is strong
  support, not verification.
- **Iteration order alone never rejects c2.** An unconstrained order is compatible with any
  observed order. The discriminator is the relation, at the boundary where the code hands it
  to the importer.

## 11. Collector changes eventually required

| change | needed for | notes |
|---|---|---|
| none | Layer 1 | shapes and digests at call boundaries are already recorded |
| **structured capture (F2)** at bindings named by the mechanics (the change's functions and the frontier) | Layer 2 relation checks | set, list, tuple or dict of digestable members; bounded, e.g. ≤ 64 tuples, arity ≤ 4, depth ≤ 2; beyond that `complete=false` and a size only; members as digests |
| **iteration events** at loop headers in mechanics-scoped functions | iteration, per-element keying | Python: `sys.monitoring` has no loop-variable event, so this needs a line/jump hook at the loop header reading the loop target (cost bounded to scoped loops). Go: the instrumenter rewrites `for … range` bodies to call `dg.Iter(site, elemDigest)`. Elements whose identity is not digestable record an ordinal only |
| small-enum value capture (F3), allowlisted classes: bool, small int, short literal from a known literal set | Case B's role and status-code outcomes | an alternative for literals: the checker digests the source literal and compares identities, with no runtime value capture. This works only if digests are unsalted (next row) |
| **a digest-domain decision** | cross-revision identity, and comparing to source literals | unsalted content digests of low-entropy values (field names, roles) can be reversed by guessing. Salting per analysis (the same salt for base and head, never stored) prevents that but breaks literal comparison. **Unresolved** |
| call-site id on call nodes | per-call-context decisions (Experiment 08's D4/D7) | not required by these primitives. Per-element keying and per-call-site keying are the same idea ("occurrence identity") and may be designed together later |

## 12. What stays unchanged

- the site identity, dependence IR, front ends and Step 1 repairs;
- Decision, Branch, Transition, Procedure (a new step type only), Rule, Regime;
- the scalar predicate language, which only gains `in {literals}`;
- status names, and the checker's sole authority;
- every Experiment 08 and 09 genome, which is valid as-is;
- the collector's default value-free policy (F2 and F3 are opt-in per binding).

## 13. Risks of over-generalizing from Baserow

1. **One case supports relations, order and iteration.** Everything in 5.2 to 5.4 is justified
   by a single change. Its shape (declared dependencies versus actual needs, levelled
   execution) is common in importers, build systems, migrations and schedulers. But this suite
   has not yet shown a second instance.
2. **Order as closure.** Baserow's importer orders by *levels*. Another system might need
   `after` without transitivity, or a priority order that is not derived from a relation. The
   design would then need a second order source, and closure is the only derivation offered.
3. **The iteration step is shaped by one loop,** a deferred run over one collection with one
   body. Nested iterations, iterations whose bodies change the collection, and early exits
   are excluded untested.
4. **The outcome at an enclosing entity** worked because cause and effect share one entry
   episode. Effects that surface in a *different* request, such as a stored bad state read
   later, would need transitions or relations persisting across entries. Experiment 09 shows
   that works for scalars, but it is untested for relations.
5. **F2 capture sizes and value classes** are guesses. Baserow's relations have fewer than 10
   tuples. Real imports can have hundreds of fields, and the complete/incomplete distinction
   will carry a lot of weight.
6. **Model rules over relations** are a new place for plausible-but-wrong semantics, e.g. a
   wrong join direction. They are checkable only at F2 bindings. Where F2 is not captured,
   they sit at `supported` indefinitely.

## 14. Open questions Case B should answer

Case B's real code is **scalar**, so these questions mostly test *restraint*, not relations:

1. Does a proposer, given the extended schema, **avoid** relations when the code does not use
   them? This is a cheap test of whether optional primitives stay optional.
2. Is `role in {banker, depositor}` with a **static literal set** enough? The allowed set is a
   literal at one call site. If a later change passes different sets from several endpoints,
   does that need a relation keyed by call site, or per-call-site context? #103 cannot tell.
3. **Value flow through an encoding.** The role is written into the token at login and read
   back on a later request. Is a transition across the token boundary, like Experiment 09's
   state, enough? Or does the token behave as a relation (principal → claims)?
4. **Outcome kinds for returned errors.** `PermissionDenied`, `NotFound` and `Unauthenticated`
   are *codes inside* one Go error type. Is the exit category plus the error type enough to
   distinguish the tests' branches? Or is F3 capture of the status code needed? This decides
   whether Outcome needs value-level kinds.
5. **The digest-domain question** (section 11): comparing an observed role digest to the source
   literal `"banker"` requires unsalted digests.

What Case B **cannot** answer: whether 5.2 to 5.4 are right. That needs a second
relation-shaped change. Of the recorded later candidates, a dependency- or ordering-driven
change would be the test. Flagsmith #8532/#8601 and Unleash #4345 should be checked for that
shape before being chosen.

## 15. Minimal implementation sequence, if approved

1. **Outcome** (5.5), with its status rules, predictor support and `outcome` evidence. It is
   supported by three shapes: Experiment 08's returned-error paths, Case B's error codes, and
   Case A's raised error. It needs no collector change.
2. **Boundary bindings** (5.1). They need no collector change. Re-run Case A's controls. The
   acceptance check is that c2 is rejected at the hook's result and the expansion boundary,
   and the real binding is verified.
3. Run **Case B** with the extended proposer instructions (outcome and boundary bindings), and
   record whether relations were avoided.
4. Only if a second relation-shaped case is identified:
   - F2 capture;
   - iteration events (Python first);
   - relation variables with join and closure derivations;
   - `for_each`;
   - the checks.

   Then re-run Case A with a fresh proposal, including controls c1 to c4 and a new seeded
   *wrong join* control.

## Recommendation

**DO NOT BUILD YET** for the relation, derived-order and iteration primitives (5.2 to 5.4).

The exact unresolved reason: they are supported by **one** case. The designated second domain
does not exercise them. Case B's real change, upstream #103 with parent equal to Case B's base,
has:
- no relation-valued runtime state (the role is scalar);
- one literal allowed set at one call site;
- a loop that only computes membership;
- no derived order, and no per-item effects.

So the design cannot yet be told apart from a Baserow-shaped fit. The evidence that would
verify it also depends on two things not yet designed or validated:
- iteration events on Python, where `sys.monitoring` has no loop-variable event;
- a decision on the digest domain, salted or unsalted.

**What does survive the evidence and could be built separately:**
- **Outcome (5.5).** Three shapes need it.
- **Boundary bindings (5.1).** They alone make c2 mechanically rejectable on today's traces.

Neither makes Case A's failure *generative*. Predicting "base raises, head completes" from
the relation still needs 5.2 to 5.4.
