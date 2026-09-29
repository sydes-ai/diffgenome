# Experiment 08: a Behavioral Genome IR on top of the evidence graph

## Hypothesis

DiffGenome can evolve from a behavioral call/composition map into a compact, *generative*
representation of internal behavior: data dependencies, decisions, relevant state, effects
and rules that generate the observed paths. A bounded LLM proposes that semantic layer;
execution and static evidence decide its status. The model's output never becomes fact
by itself.

One case: simplebank `5b03c1d`, "reject transfers exceeding source account balance". Entry
`Server.createTransfer`. Everything is in `docs/runs/genome-simplebank-5b03c1d/`. No Sydes
change and no change to the integration contract.

## A. Schema (`diffgenome-genome/0`, experimental, `src/diffgenome/genome.py`)

The evidence graph stays the substrate. The genome is a layer above it. Every item carries
`derived_by`, `evidence` (a list of checkable references) and `status`.

| element | fields | derived by |
|---|---|---|
| Entity | symbol, role | collector: the change artifact's nodes and boundaries |
| Variable | name, origin (request / state / derived / environment), **definition** | model |
| DataDependency | source variable → sink (decision or entity), transform | model |
| Decision | entity, inputs, predicate, **order**, true/false Branch (returns, calls, absent, stops, effect) | model |
| Effect, Transition | kind/target/condition; state before/action/after | model |
| BehavioralRule | inputs, relevant state, condition, consequences, **decision** it summarizes | model |
| Regime | name, facts, members: a behavioral equivalence class of executions | model |
| EvidenceRef | `source` (file, line, text) · `execution` (test, calls in order, absent, decoded returns) · `edge` | model cites; checker checks |

The status of every item is assigned by `establish()` only. The model assigns none.

| status | rule |
|---|---|
| observed_fact | collected at runtime (entities, paths, decoded return values) |
| static_fact | read from source (the deterministic `if` scan) |
| hypothesis | no evidence cited, or a cited reference does not check out |
| supported | every cited reference checks out |
| verified | *decisions*: supported, and cites an `if` site from the deterministic scan, and both branches are observed with a decodable outcome, and no execution contradicts them. *rules*: summarize a verified decision, and their condition uses only that decision's inputs |
| rejected | an execution contradicts it |

Two pieces of deterministic evidence were cheap and decisive:
- **Decoded return values.** The collectors digest scalars as `sha256("<kind>:<value>")`, so
  a boolean result is decodable exactly. That makes "`checkSufficientBalance` returned
  false in this execution" an observed fact, not an inference.
- **The `if` scan.** Every `if <cond> {` line in the entry's files is listed, with no
  semantics attached.

## B. Method

1. **Bounded context (deterministic, `experiments/genome/build_context.py`).** The bundle
   holds the change, the change-centred behavioral map, the observed paths under
   `createTransfer` with decoded returns, the `if` sites, the source of the changed symbols
   and their direct callees, and the test source: 856 lines in total, digest
   `a0fd457517e27822`. A rebuild gives the same digest.
2. **Holdout.** The paths of four executions were withheld from the model:
   `InsufficientBalance` (case A itself), `TransferTxError`, `ToAccountCurrencyMismatch` and
   `UnauthorizedUser`. The only visible `checkSufficientBalance` execution was `OK`, which
   returned `true`. The false branch had to come from source. One leak: the behavioral map
   shows that `checkSufficientBalance → errorResponse` was observed once, but not in which
   test.
3. **Model.** A fresh Opus instance (`claude-opus-5-5`) read only the bundle and wrote
   `proposals.json`. One follow-up asked it only for machine-readable definitions of the
   derived variables it had proposed (`definitions.json`). That made two model calls in
   total, about 86k subagent tokens.
4. **Establish.** `experiments/genome/establish.py` checks every reference against all 11
   executions, the graph and the source, then assigns statuses.
5. **Generative check.** For each test, the model's `test_facts` (read from test source,
   themselves hypotheses) are run through the genome to predict a path. The prediction must
   match what executed in order, in count, and with the predicted-absent entities absent.
   The two scenarios A and B are stated directly as numbers.
6. **Controls.** Four proposals with seeded errors were run through the same pipeline.

## C. The genome

`genome.md` (human-readable) and `genome.json`. The model proposed 12 variables, 6 data
dependencies, 10 decisions (D0–D9), 6 effects, 1 transition, 5 rules and 6 regimes. The
compact core:

```
R1 request shape      !request.currency_supported || request.amount <= 0   → 400, no store access
R2 account eligibility from, then to: exists (404/500) and currency matches (400)
R3 ownership          !from_account.owned_by_auth (after from, before to)  → 401, to never looked up
R4 balance guard      from_account.balance < request.amount                → checkSufficientBalance=false, 400, TransferTx never called
R5 persist            all gates pass                                       → TransferTx; 200, or 500 if it errors
```

| | supported | verified | hypothesis | rejected |
|---|---|---|---|---|
| decisions (10) | 8 | **2**: D1 currency binding, D8 balance guard | 0 | 0 |
| rules (5) | 4 | **1**: R4 balance guard | 0 | 0 |
| variables, dependencies, effects, transition, regimes | all | – | – | – |

- **D8 is verified.** It cites the `if account.Balance < amount {` site at transfer.go:85.
  Its true branch is observed returning `false` in `InsufficientBalance`, with
  `errorResponse` and no `TransferTx`. Its false branch is observed returning `true` in `OK`
  and `TransferTxError`, reaching `TransferTx`.
- **R1 stays supported.** It summarizes verified D1, but its condition also covers
  `request.amount <= 0`, which D1 does not decide.
- **The other eight decisions are supported only.** Their citations check out, but there is
  no decodable per-branch outcome: `validAccount` returns `(Account, bool)`, which the
  collector does not digest, and ownership and binding produce no call of their own.

## D. Is it generative?

**Per test.** Test facts go through the genome's decisions to a predicted path, which is
compared with what executed, requiring order, count and absences to match.

| | exact |
|---|---|
| all 11 executions under the entry | **11/11** |
| the 4 withheld from the model | **4/4** |

The withheld `InsufficientBalance` was predicted as
`<anon>@8 → validAccount → GetAccount → validAccount → GetAccount → checkSufficientBalance →
errorResponse`, with `TransferTx` never reached and the path stopping at D8. That is exactly
what executed, and the model never saw that path.

**Scenarios, using decisions at supported or better:**

```
A  amount=10, balance=9   (other gates pass)
   → D1 false · D2 false · D3 false · D4 false · D5 false · D6 false · D7 false · D8 TRUE (stop)
   → <anon>@8 → validAccount → GetAccount → validAccount → GetAccount → checkSufficientBalance → errorResponse
     TransferTx never reached
B  amount=10, balance=10
   → … D8 false · D9 false (stop)
   → … → checkSufficientBalance → TransferTx; errorResponse absent
```

**Using verified decisions only**, both scenarios are *indeterminate* at D0: the
auth-middleware decision is only supported. With only verified knowledge the genome cannot
say what happens, and it says so instead of guessing.

**Before the definition follow-up**, A and B were indeterminate. The model had encoded the
guard as the boolean `balance_sufficient`, with its meaning `balance >= amount` in prose
only. The predictor cannot evaluate `amount > balance` without a machine-readable link.
This is the one schema addition the experiment forced (`Variable.definition`). The model
supplied the definition when asked, and correctly declined to invent new variables for the
other three derived booleans (currency match, ownership).

## E. Controls: does the checker catch wrong semantics?

| seeded error | caught by | D8 | exact predictions | case A |
|---|---|---|---|---|
| inverted consequence (TransferTx still called when insufficient) | the withheld `InsufficientBalance` execution | **rejected** | 8/11 | indeterminate at D8 |
| fabricated citation (`<=` for `<`) | source check | **hypothesis** | 8/11 | indeterminate at D8 |
| false execution claim (`OK` calls `errorResponse`) | execution check | **rejected** | 8/11 | indeterminate at D8 |
| swapped decision order (ownership after the to-account lookup) | **not by the checker**; only by prediction | verified | 10/11 (`UnauthorizedUser` fails) | unaffected |

**Three flaws in my own tooling, found and fixed during the experiment:**
1. **The predictor skipped unestablished decisions.** With D8 demoted, case A predicted
   `TransferTx` reached, silently treating the guard as absent. A decision site that exists
   but whose semantics are unestablished now stops prediction as indeterminate.
2. **"Verified" accepted any valid source citation.** It now requires an `if` site from the
   deterministic scan.
3. **A rule inherited "verified" from its decision even when its condition covered more.**
   R1 was the example; that is now excluded.

## F. Compression

| raw evidence | | genome | |
|---|---|---|---|
| executions (whole suite / through the entry) | 50 / 11 | entities (collector) | 9 |
| call nodes in those 11 | 334 | variables | 12 (1 with a machine-readable definition) |
| state facts in those 11 | 536 | decisions | 10 |
| path steps under the entry | 65 | rules | 5 |
| distinct path shapes | 6 | regimes | 6 |
| graph edges (whole repo) | 379 | | |

**Example.** R2, "an account must exist and match the request currency, applied to the
source then the destination", is one rule over two decisions per account. It generates 5
of the 11 executions: `FromAccountNotFound`, `GetAccountError`, `FromAccountCurrencyMismatch`,
`ToAccountNotFound` and `ToAccountCurrencyMismatch`. Those 5 fall into only 2 distinct call
shapes, because "not found" and "currency mismatch" both call `GetAccount` then
`errorResponse`. The call-shape view cannot tell them apart; the genome can, through
decisions D3 versus D4, and D6 versus D7. Any new input can be classified by it, not only
those 5. More broadly, 10 decisions with explicit
branch consequences reproduce all 11 executions exactly. An 11-row table of paths would do
the same for these 11 inputs, but not for a new one. That difference is the point.

The compression is real but modest here, because the handler is a straight gate sequence.
The claim is that 334 call nodes and 65 path steps reduce to an ordered list of 10 guarded
decisions. It is not that the genome is small in bytes.

## G. What the LLM contributed, and what deterministic machinery must keep doing

**LLM was useful for:**
- **Predicate abstraction.** It turned `if !server.checkSufficientBalance(...)` plus
  `if account.Balance < amount` into one decision over `request.amount` and
  `from_account.balance`, including the negation across the call boundary.
- **Semantic naming** of variables in request, state and derived form, with origins.
- **Decision ordering** along the path, including the non-obvious placement of ownership
  between the two account lookups.
- **Regime grouping.** Six equivalence classes, R2 applied twice.
- **Reading test fixtures into input facts** (`insufficientAccount.Balance = amount - 1`
  gives balance 9 and amount 10).
- **Honest unknowns.** It flagged that random test balances are unobservable, that
  `NoAuthorization` never reaches the handler, and that the order of the binding checks is
  a guess.
- **Relevance selection and rule summarization**: 5 rules from 10 decisions.

**Deterministic machinery was required for:**
- **Runtime path truth and branch outcomes.** The decoded `=true/=false` values are what
  made D1 and D8 verifiable. No model output could substitute for them.
- **Every status decision**, including rejecting the inverted consequence using a test the
  model never saw.
- **Citation checking.** The fabricated `<=` was caught by a text check.
- **Identity** of entities and stand-ins (collector symbols, resolver claims).
- **The `if` sites** that anchor predicates.
- **Provenance**: bundle digest, holdout list, derived_by on every item.

**Not established by either, today:**
- **Actual data dependencies.** "`request.amount` → D8" is supported by a citation whose text
  contains both names. It is not a traced dataflow.
- **Operand values at a decision.** Balances and amounts are hashed; only booleans decode.
  The predicate `balance < amount` is therefore verified through its boolean outcome plus
  the source line, not through observed operands.
- **Decision order.** No direct check exists; it is only testable through prediction (control c4).
- **Mutations and transitions.** Every store call is a mock; TransferTx's effect on balances
  is a gap. The one proposed transition is a citation, not an observation.
- **Branches with no decodable outcome**: `validAccount`, ownership, binding.

## H. Custom models, architecturally only

The repeated tasks in this pass, candidates for small models later with the checker left
unchanged:
- **Predicate abstraction across call boundaries**: an `if` line and a boolean helper become
  one predicate over named inputs.
- **Test-fixture to input-facts extraction**: structured, checkable against executions.
- **Decision ordering along a handler**: checkable by prediction.
- **Regime clustering**: grouping executions by the decision that stops them. This is
  nearly deterministic once decisions exist.
- **Relevant-state ranking**: which of 536 state facts matter. The model used none of them
  here; balances were read from test source.

## I. Final assessment

1. **Is the graph a reasonable substrate?** Yes, as far as it goes. Entities, ordered paths,
   stand-ins, outcomes and decoded returns were exactly what the checker needed. What it lacks
   is operand values at decisions and undigested multi-value returns.
2. **What schema additions were necessary?** Decisions with ordered, stop-aware branches;
   machine-readable `Variable.definition`; checkable evidence refs; the six-way status; and
   Regime. Transition and Effect were barely usable in this case.
3. **Could Opus infer useful dependencies, predicates and effects from bounded evidence?**
   Yes. From 856 lines it produced a decision structure that predicts all 11 paths exactly,
   including 4 it never saw. It needed one prompt for machine-readable definitions.
4. **What was supported versus hypothesized?** Verified: the balance guard (D8, R4) and
   currency binding (D1). Supported: the other 8 decisions and 4 rules, all variables,
   dependencies, effects and regimes. No proposal was rejected; the seeded controls were.
   "Supported" means cited, not traced.
5. **Did it compress?** Yes, structurally: 334 call nodes and 6 path shapes became 10
   ordered decisions and 5 rules that classify unseen inputs. The gain is generality, not bytes.
6. **Could it reconstruct `amount > balance` versus `amount <= balance`?** Yes, symbolically,
   at supported confidence: A stops at the balance guard with TransferTx never reached; B
   reaches TransferTx. At verified-only confidence it correctly declines.
7. **What was impossible to derive reliably?** Operand-level truth of predicates, real
   dataflow, mutations of persistent state, decision order without prediction, and any
   behavior of the real store.
8. **What should stay deterministic?** Status assignment, citation and execution checks,
   branch-outcome decoding, `if`-site anchoring, identity, the holdout discipline and
   provenance. Prediction must stay sound: unknown semantics stop it.
9. **What suits LLM or custom models?** Predicate abstraction, naming, ordering,
   fixture-to-facts extraction, regime grouping and rule summarization.
10. **Continue, or stay a map?** Continue, narrowly. The result is strong on one case: a
    generative, checkable description that predicted unseen executions, with three bad
    proposals caught and no silent promotion. It is also the easiest kind of handler, a
    linear gate sequence with boolean helpers. The next honest test is a case whose
    behavior depends on state and effects, not guards, together with one cheap collector
    addition: recording operand buckets at `if` sites, so predicates can be verified from
    observed values rather than only from outcomes.

Deferred as instructed: OS plane, languages, framework logic, concurrency, graph database,
UI, benchmarks, model training, deep dataflow, and any Sydes change.
