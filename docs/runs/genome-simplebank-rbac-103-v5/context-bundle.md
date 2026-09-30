# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is simplebank #103 (upstream techschool/simplebank#103; fork sydes-examples/simplebank#5) (base 6e267986 → head 2e2094e2):
"add role-based access control (RBAC)". Users get a `role` (a new column, default `depositor`; constants `util.DepositorRole` and `util.BankerRole`). Token creation takes the role and stores it in the token payload. The gRPC `authorizeUser` now takes the accessible roles of the calling endpoint and rejects a verified token whose role is not among them (`hasPermission`). `UpdateUser` passes both roles and lets a banker update any user, while any other role may update only itself.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- decision sites (`if`) with stable ids `br:...` (per revision), source predicate, operand
  origins (local def-use), and the (site, outcome) pairs required to reach them;
- for every call and store: which (site, outcome) pairs it requires;
- for the tests shown (at head): the ordered event log of the relevant calls, each call's
  argument shapes with value digests (`#abcd12`: equal digests = equal values; contents are
  not recorded), results, the observed outcome (T/F) of every decision site in those calls,
  and every call's observed EXIT (returned / returned-error / raised / panic). The digest
  `#5da3a4` is Go's `nil`.

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior of the head (which calls happen, which decisions
go which way, how each entry call exits). A machine checks everything you cite and assigns
status; you assign none. Tests are withheld (traces not shown; source shown). Write scenarios
for them; they will be predicted and compared with what executed.

## The genome format (fixed; the checker and predictor implement exactly this)

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": null
                  | {"fact": "<receiver/global state fact>", "kind": "is_set|sign|bool"}
                  | {"at": {"entity": "<function>", "point": "arg:<name>" | "result"},
                     "kind": "is_set" | "changed_from:arg:<name>" | "size" | "bool"}
                  | {"at": {...}, "kind": "identity", "scope": "call" | "execution"}
                  | {"at": {...}, "kind": "equals_literal", "scope": "call" | "execution",
                     "literal": {"lang": "go", "type": "string|int|uint8|...|bool|nil", "value": <v>,
                                 "source": {"file": "<repo path>", "line": N}}}
                  | [<several of the above>],
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity", "site": "br:... (a HEAD site id)", "inputs": [...],
                "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool,
                                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "regions": [{"id", "entity": "<the enclosing function>", "head": "<the observed family that starts each repetition: a function name or site:br:...>",
              "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...], "evidence": [...]}],
 "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", "R:<region id>", ...],
                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value},
                               "calls": [{"entity": "<entity>", "facts": {<variable>: value},
                                          "occurrences": {"<region id>": [{"facts": {<variable>: value}}, ...]}}],
                               "phenotype": {"head": "<exit of the entry call>", "why": "<one sentence from your rules>"}}},
 "unknowns": [{"what", "why"}]
}

**Boundary bindings.** A variable may be bound to an identity-level fact at a call boundary of
an entity: `is_set` (the argument/result is not None), `changed_from:arg:<name>` (the result's
digest differs from that argument's digest), `size` (an argument's collection size), `bool`.
The checker reads these from the digests and shapes you see in the logs, per call. Argument
facts are known when the call starts; result and change facts when it ends. A transition of
an entity that sets a boundary-bound variable is checked against that call's observed
boundary: when the entry state cannot decide the path, the checker follows the branches that
actually executed in that call (a decision with an atomic predicate `v` / `!v` then binds v).

**Value identity and literals.** A binding of kind `identity` gives the variable an OPAQUE
value: the digest seen at that boundary, never decoded. With `scope: "execution"`, the value is
taken from that boundary's occurrences earlier in the same test (it must be unique there, or it
is unknown); with `scope: "call"` (default) from the call being judged. A variable with a LIST
of two or more `identity` bindings claims the SAME value appears at all of them in one test:
the checker verifies that from observed digest equality (equal in at least 2 tests carrying at
least 2 different values), rejects it if any test shows them different, and never infers flow
(only equality). Identity variables are compared only with `==` / `!=`. In scenarios, give an
identity variable a LABEL (any string, e.g. "access"): for shown tests the checker requires
equal labels exactly where the observed identities are equal. A binding of kind
`equals_literal` is true when the boundary value equals a literal WRITTEN in the source at the
cited line (bool, nil, an integer, or a short plain string); the checker confirms the literal on
that line and compares digests, it never decodes other values. Scenario facts for any bound
variable (boundary, identity, literal) are checked against the matching call in shown tests.

**Evidence and prediction eligibility.** Every item must cite checkable evidence; an item
with none stays a hypothesis and cannot drive a prediction. A supported item that some shown
test contradicts (e.g. its replayed outcome sequence differs) cannot drive a prediction either.
A variable with two or more identity bindings is evidenced by its bindings themselves.

**Outcome.** An exit is one of `returned`, `returned-error[:<kind>]`, `raised[:<kind>]`,
`panic[:<kind>]`, `cancelled` (`completed` = `returned`). `<kind>` is the runtime type name,
e.g. `raised:django.db.utils.DataError`. A branch's outcome names the function whose exit it
determines, which may be the deciding function or one ENCLOSING it (an effect that surfaces
later in the same call). A procedure's outcome is its entity's exit when its steps complete
without a stopping branch. Exits are compared with the observed exit of that function's calls,
never with test results.

**Repeated regions and occurrence facts.** Repeated region placement is supplied by mechanics.
Concrete occurrence facts are supplied by the scenario. Do not invent occurrence count, nesting
or order. A region (`regions`) is ONE body that runs once per occurrence of an OBSERVED repeated
region of its enclosing function (`entity`); its `head` must be the family that the observed
structure says starts every repetition, and its steps must follow the observed order inside one
repetition. The enclosing function's procedure places it with the step `"R:<region id>"`. The
genome never states how many times a region runs: a scenario's call of the enclosing function
supplies `occurrences: {"<region id>": [...]}`, one item per concrete occurrence in order, each
with that occurrence's facts (read them from the test's input; the k-th item is the k-th
repetition). For the shown tests the checker aligns your k-th item with the observed k-th
repetition and checks every fact it can observe there (boundary facts of the calls inside it,
and variables your atomic decisions `v` / `!v` bind from their observed outcomes); a
contradicted fact or a wrong count makes that prediction indeterminate.

**Execution structure is a constraint, not yours to choose.** The section "Observed execution
structure" below is derived mechanically from the shown executions: which function runs
during which (containment), the order of phases inside a function, which calls form a
repeated region, and the order of calls and decisions inside one repetition. Call nesting and
relative procedural placement supplied by mechanics are constraints. Do not reorder calls, and
do not hoist a call or a decision outside its observed enclosing function. The checker judges
every procedure's structure (which calls and decisions it places inside which function, and
the order of consecutive steps) against these facts, and a prediction that places a call or a
decision where it was never observed is indeterminate. Express a repetition inside its enclosing function as a region (see Repeated regions and occurrence facts, above), never by hoisting it.

**Not available** (deliberately): relation-valued variables, derived orders, iteration over
collections (loop variables, item identity across calls). If the behavior needs them, say so
precisely in `unknowns`; do not simulate them with per-instance variable names.

Semantics used by the predictor:
- A scenario's `calls` are the entry calls in order. A call of an entity with a procedure runs
  it; a call of an entity the genome says nothing about is recorded and skipped; a call of an
  entity that has decisions but no procedure stops the prediction (so give every entity whose
  decisions you list a procedure, or reach its decisions through another entity's procedure).
  "call:X" records a call and, if X has a procedure, runs it; "T:id" applies a transition
  (literals true/false/none/integers, `var`, `!var`, `var + k`, `var - k`, `max(0, var - k)`);
  "D:id" evaluates a decision and runs the taken branch's `steps` ONLY (a branch's
  `calls` are descriptive, what it reaches, and are never executed); a branch
  with `stops: true` ends the entity (inside a region too: there is no `continue`). "R:id"
  runs region id once per occurrence the current scenario call supplies, in order: that
  occurrence's facts hold during its body only (they are restored afterwards; variables bound
  to receiver/global state persist); a region with no supplied occurrences stops the prediction.
  Predicates: booleans/integers, `!name`, comparisons (identities: `==` / `!=` only),
  `&&`, `||`, no parentheses. A scenario
  lists every entry call, in order, with the facts that hold for that call and, for repeated
  regions inside it, per-occurrence facts.
- SCORING covers every observed evaluation of EVERY site listed under "Required sites" below
  (the changed functions and functions nested in them), in order, per test. A site no decision
  covers makes the prediction indeterminate. Predicted exits are compared per entity with the
  observed exits of that entity's calls.
- `phenotype` is your claim about the entry call's exit; scored separately.
- Use only site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"<repo-relative path>","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:req>"}
  {"kind":"boundary","entity":"<function>","point":"arg:<name>|result","binding":"is_set|changed_from:arg:<name>|size|bool","value":<value>,"test":"<shown test name>"}
  {"kind":"outcome","entity":"<function>","exit":"<exit>","test":"<shown test name>"}
  Cite only shown tests, and only head sites, in branch/boundary/outcome evidence.
- Prefer few, generative rules. Be honest in `unknowns`.


## Required sites (head ids)

Every OBSERVED evaluation of these sites is scored, in every test. Sites the shown tests never evaluated are marked; a withheld test that evaluates one needs a decision for it.

- br:9c4f387be39d go:api.Server.loginUser line 89: `err != nil`   (not evaluated in the shown tests)
- br:365f01cfaf9a go:api.Server.loginUser line 95: `err != nil`   (not evaluated in the shown tests)
- br:8c4975b74bce go:api.Server.loginUser line 96: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:67ea910da26c go:api.Server.loginUser line 105: `err != nil`   (not evaluated in the shown tests)
- br:620e5470e915 go:api.Server.loginUser line 115: `err != nil`   (not evaluated in the shown tests)
- br:f256c2c9ce95 go:api.Server.loginUser line 125: `err != nil`   (not evaluated in the shown tests)
- br:31f8086bdd5e go:api.Server.loginUser line 139: `err != nil`   (not evaluated in the shown tests)
- br:7f4a03494e61 go:api.Server.renewAccessToken line 24: `err != nil`   (not evaluated in the shown tests)
- br:8a53d4418573 go:api.Server.renewAccessToken line 30: `err != nil`   (not evaluated in the shown tests)
- br:c25e0917e397 go:api.Server.renewAccessToken line 36: `err != nil`   (not evaluated in the shown tests)
- br:03efe4cada2e go:api.Server.renewAccessToken line 37: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:eca7bb637933 go:api.Server.renewAccessToken line 45: `session.IsBlocked`   (not evaluated in the shown tests)
- br:0cb1367c07fc go:api.Server.renewAccessToken line 51: `session.Username != refreshPayload.Username`   (not evaluated in the shown tests)
- br:f2bc1697337d go:api.Server.renewAccessToken line 57: `session.RefreshToken != req.RefreshToken`   (not evaluated in the shown tests)
- br:0f24bd276232 go:api.Server.renewAccessToken line 63: `time.Now().After(session.ExpiresAt)`   (not evaluated in the shown tests)
- br:ce6bba1a95f1 go:api.Server.renewAccessToken line 74: `err != nil`   (not evaluated in the shown tests)
- br:930116d7ba7e go:gapi.Server.LoginUser line 19: `violations != nil`   (not evaluated in the shown tests)
- br:8766f154fd07 go:gapi.Server.LoginUser line 24: `err != nil`   (not evaluated in the shown tests)
- br:aa1290a8b57d go:gapi.Server.LoginUser line 25: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:fd4e92e7cbac go:gapi.Server.LoginUser line 32: `err != nil`   (not evaluated in the shown tests)
- br:f3feb339909f go:gapi.Server.LoginUser line 41: `err != nil`   (not evaluated in the shown tests)
- br:4ec58fbc60ce go:gapi.Server.LoginUser line 50: `err != nil`   (not evaluated in the shown tests)
- br:484cec688a66 go:gapi.Server.LoginUser line 64: `err != nil`   (not evaluated in the shown tests)
- br:0746154f1c47 go:gapi.Server.UpdateUser line 20: `err != nil`
- br:af0e24f4367b go:gapi.Server.UpdateUser line 25: `violations != nil`
- br:01807a7b80a2 go:gapi.Server.UpdateUser line 29: `authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`
- br:815be3bfb43a go:gapi.Server.UpdateUser line 45: `req.Password != nil`
- br:5f17958f3d3f go:gapi.Server.UpdateUser line 47: `err != nil`   (not evaluated in the shown tests)
- br:17f2bce25a0f go:gapi.Server.UpdateUser line 63: `err != nil`
- br:fb1ba40798cf go:gapi.Server.UpdateUser line 64: `errors.Is(err, db.ErrRecordNotFound)`
- br:e3505bc4c4b9 go:gapi.Server.authorizeUser line 19: `!ok`
- br:a572eeb6a4c8 go:gapi.Server.authorizeUser line 24: `len(values) == 0`
- br:4393757b65d7 go:gapi.Server.authorizeUser line 30: `len(fields) < 2`
- br:2e2f712d6301 go:gapi.Server.authorizeUser line 35: `authType != authorizationBearer`
- br:c71158777bce go:gapi.Server.authorizeUser line 41: `err != nil`
- br:c1bc39962889 go:gapi.Server.authorizeUser line 45: `!hasPermission(payload.Role, accessibleRoles)`
- br:92f48828a554 go:gapi.hasPermission line 54: `userRole == role`
- br:d9f1e0c214f9 go:token.JWTMaker.CreateToken line 29: `err != nil`   (not evaluated in the shown tests)
- br:b4114c26b15a go:token.NewPayload line 28: `err != nil`
- br:0713394c9923 go:token.PasetoMaker.CreateToken line 34: `err != nil`

## Observed execution structure (deterministic; shown executions only)

```
(from 5 shown execution(s))
- go:db/sqlc.Queries.UpdateUser: 2 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 2 exec)
    runs during: go:gapi.Server.UpdateUser (in 2 exec)
- go:gapi.Server.UpdateUser: 5 occurrence(s)
    nearest modeled caller: <root> (in 5 exec)
    runs during: <root> (in 5 exec)
- go:gapi.Server.authorizeUser: 5 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec)
- go:gapi.convertUser: 1 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 1 exec)
    runs during: go:gapi.Server.UpdateUser (in 1 exec)
- go:gapi.hasPermission: 4 occurrence(s)
    nearest modeled caller: go:gapi.Server.authorizeUser (in 4 exec)
    runs during: go:gapi.Server.UpdateUser (in 4 exec), go:gapi.Server.authorizeUser (in 4 exec)
- go:gapi.validateUpdateUserRequest: 4 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 4 exec)
    runs during: go:gapi.Server.UpdateUser (in 4 exec)
- go:token.NewPayload: 4 occurrence(s)
    nearest modeled caller: go:token.PasetoMaker.CreateToken (in 4 exec)
    runs during: go:token.PasetoMaker.CreateToken (in 4 exec)
- go:token.PasetoMaker.CreateToken: 4 occurrence(s)
    nearest modeled caller: <root> (in 4 exec)
    runs during: <root> (in 4 exec)
- go:token.PasetoMaker.VerifyToken: 4 occurrence(s)
    nearest modeled caller: go:gapi.Server.authorizeUser (in 4 exec)
    runs during: go:gapi.Server.UpdateUser (in 4 exec), go:gapi.Server.authorizeUser (in 4 exec)
- go:token.Payload.Valid: 4 occurrence(s)
    nearest modeled caller: go:token.PasetoMaker.VerifyToken (in 4 exec)
    runs during: go:gapi.Server.UpdateUser (in 4 exec), go:gapi.Server.authorizeUser (in 4 exec), go:token.PasetoMaker.VerifyToken (in 4 exec)

inside go:gapi.Server.UpdateUser:
  family go:db/sqlc.Queries.UpdateUser: in 2 occurrence(s), once
  family go:gapi.Server.authorizeUser: in 5 occurrence(s), once
  family go:gapi.convertUser: in 1 occurrence(s), once
  family go:gapi.validateUpdateUserRequest: in 4 occurrence(s), once
  family site:br:01807a7b80a2: in 3 occurrence(s), once
  family site:br:0746154f1c47: in 5 occurrence(s), once
  family site:br:17f2bce25a0f: in 2 occurrence(s), once
  family site:br:815be3bfb43a: in 2 occurrence(s), once
  family site:br:af0e24f4367b: in 4 occurrence(s), once
  family site:br:fb1ba40798cf: in 1 occurrence(s), once
  go:db/sqlc.Queries.UpdateUser BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:db/sqlc.Queries.UpdateUser BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:db/sqlc.Queries.UpdateUser BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:0746154f1c47  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:01807a7b80a2 BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:01807a7b80a2 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0746154f1c47 BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0746154f1c47 BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:17f2bce25a0f BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:17f2bce25a0f BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:815be3bfb43a BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:815be3bfb43a BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:815be3bfb43a BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:815be3bfb43a BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE go:gapi.convertUser  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside go:gapi.Server.authorizeUser:
  family go:gapi.hasPermission: in 4 occurrence(s), once
  family go:token.PasetoMaker.VerifyToken: in 4 occurrence(s), once
  family site:br:2e2f712d6301: in 4 occurrence(s), once
  family site:br:4393757b65d7: in 4 occurrence(s), once
  family site:br:a572eeb6a4c8: in 4 occurrence(s), once
  family site:br:c1bc39962889: in 4 occurrence(s), once
  family site:br:c71158777bce: in 4 occurrence(s), once
  family site:br:e3505bc4c4b9: in 5 occurrence(s), once
  go:gapi.hasPermission BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c71158777bce  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:2e2f712d6301 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:2e2f712d6301 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:4393757b65d7 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:4393757b65d7 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:4393757b65d7 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:c71158777bce BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:c71158777bce BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:a572eeb6a4c8  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))

inside go:gapi.validateUpdateUserRequest:
  family site:br:444b7eee95f8: in 4 occurrence(s), once
  family site:br:57793335771a: in 4 occurrence(s), once
  family site:br:578b58ceb4d3: in 4 occurrence(s), once
  family site:br:864c3600c3d5: in 4 occurrence(s), once
  family site:br:9558e38bf1ec: in 4 occurrence(s), once
  family site:br:f63e639d4185: in 4 occurrence(s), once
  site:br:444b7eee95f8 BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:57793335771a BEFORE site:br:444b7eee95f8  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:57793335771a BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:57793335771a BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:57793335771a BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:57793335771a BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:9558e38bf1ec BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))

inside go:token.PasetoMaker.CreateToken:
  family go:token.NewPayload: in 4 occurrence(s), once
  family site:br:0713394c9923: in 4 occurrence(s), once
  go:token.NewPayload BEFORE site:br:0713394c9923  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))

inside go:token.PasetoMaker.VerifyToken:
  family go:token.Payload.Valid: in 4 occurrence(s), once
  family site:br:0607e4d952f6: in 4 occurrence(s), once
  family site:br:c7d403dfabc3: in 4 occurrence(s), once
  go:token.Payload.Valid BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0607e4d952f6 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0607e4d952f6 BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
```

## Mechanics at HEAD (deterministic, intra-procedural)

### db/sqlc.Queries.UpdateUser  (db/sqlc/user.sql.go)
- call `q.db.QueryRow` line 97 requires: —
- call `row.Scan` line 106 requires: —

### gapi.Server.authorizeUser  (gapi/authorization.go)
- site br:e3505bc4c4b9 line 19: `!ok` | operands: ok ← call:metadata.FromIncomingContext#1 | requires: — | then exits: True, else exits: False
- site br:a572eeb6a4c8 line 24: `len(values) == 0` | operands: values ← call:md.Get | requires: br:e3505bc4c4b9=F | then exits: True, else exits: False
- site br:4393757b65d7 line 30: `len(fields) < 2` | operands: fields ← call:strings.Fields | requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F | then exits: True, else exits: False
- site br:2e2f712d6301 line 35: `authType != authorizationBearer` | operands: authType ← call:strings.ToLower; authorizationBearer ← global:authorizationBearer | requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F | then exits: True, else exits: False
- site br:c71158777bce line 41: `err != nil` | operands: err ← call:server.tokenMaker.VerifyToken#1 | requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F | then exits: True, else exits: False
- site br:c1bc39962889 line 45: `!hasPermission(payload.Role, accessibleRoles)` | operands: payload.Role ← call:server.tokenMaker.VerifyToken#0.Role; accessibleRoles ← param:accessibleRoles | requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F & br:c71158777bce=F | then exits: True, else exits: False
- call `metadata.FromIncomingContext` line 18 requires: —
- call `fmt.Errorf` line 20 requires: br:e3505bc4c4b9=T
- call `md.Get` line 23 requires: br:e3505bc4c4b9=F
- call `len` line 24 requires: br:e3505bc4c4b9=F
- call `fmt.Errorf` line 25 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=T
- call `strings.Fields` line 29 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F
- call `len` line 30 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F
- call `fmt.Errorf` line 31 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=T
- call `strings.ToLower` line 34 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F
- call `fmt.Errorf` line 36 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=T
- call `server.tokenMaker.VerifyToken` line 40 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F
- call `fmt.Errorf` line 42 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F & br:c71158777bce=T
- call `hasPermission` line 45 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F & br:c71158777bce=F
- call `fmt.Errorf` line 46 requires: br:e3505bc4c4b9=F & br:a572eeb6a4c8=F & br:4393757b65d7=F & br:2e2f712d6301=F & br:c71158777bce=F & br:c1bc39962889=T

### gapi.hasPermission  (gapi/authorization.go)
- site br:92f48828a554 line 54: `userRole == role` | operands: userRole ← param:userRole; role ← unknown:UNKNOWN_DEPENDENCE:loop-variable | requires: ?loop | then exits: True, else exits: False

### gapi.convertUser  (gapi/converter.go)
- call `timestamppb.New` line 14 requires: —
- call `timestamppb.New` line 15 requires: —

### gapi.Server.UpdateUser  (gapi/rpc_update_user.go)
- site br:0746154f1c47 line 20: `err != nil` | operands: err ← call:server.authorizeUser#1 | requires: — | then exits: True, else exits: False
- site br:af0e24f4367b line 25: `violations != nil` | operands: violations ← call:validateUpdateUserRequest | requires: br:0746154f1c47=F | then exits: True, else exits: False
- site br:01807a7b80a2 line 29: `authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()` | operands: authPayload.Role ← call:server.authorizeUser#0.Role; util.BankerRole ← global:util.BankerRole; authPayload.Username ← call:server.authorizeUser#0.Username; req ← param:req | requires: br:0746154f1c47=F & br:af0e24f4367b=F | then exits: True, else exits: False
- site br:815be3bfb43a line 45: `req.Password != nil` | operands: req.Password ← param:req.Password | requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F | then exits: False, else exits: False
- site br:5f17958f3d3f line 47: `err != nil` | operands: err ← call:req.GetPassword, call:util.HashPassword, global:util, param:req | requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:815be3bfb43a=T | then exits: True, else exits: False
- site br:17f2bce25a0f line 63: `err != nil` | operands: err ← call:server.store.UpdateUser#1 | requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F | then exits: True, else exits: False
- site br:fb1ba40798cf line 64: `errors.Is(err, db.ErrRecordNotFound)` | operands: errors ← global:errors; err ← call:server.store.UpdateUser#1; db.ErrRecordNotFound ← global:db.ErrRecordNotFound | requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:17f2bce25a0f=T | then exits: True, else exits: False
- call `server.authorizeUser` line 19 requires: —
- call `unauthenticatedError` line 21 requires: br:0746154f1c47=T
- call `validateUpdateUserRequest` line 24 requires: br:0746154f1c47=F
- call `invalidArgumentError` line 26 requires: br:0746154f1c47=F & br:af0e24f4367b=T
- call `req.GetUsername` line 29 requires: br:0746154f1c47=F & br:af0e24f4367b=F
- call `status.Errorf` line 30 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=T
- call `req.GetUsername` line 34 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F
- call `req.GetFullName` line 36 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F
- call `req.GetEmail` line 40 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F
- call `req.GetPassword` line 46 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:815be3bfb43a=T
- call `util.HashPassword` line 46 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:815be3bfb43a=T
- call `status.Errorf` line 48 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:815be3bfb43a=T & br:5f17958f3d3f=T
- call `time.Now` line 57 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:815be3bfb43a=T & br:5f17958f3d3f=F
- call `server.store.UpdateUser` line 62 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F
- call `errors.Is` line 64 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:17f2bce25a0f=T
- call `status.Errorf` line 65 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:17f2bce25a0f=T & br:fb1ba40798cf=T
- call `status.Errorf` line 67 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:17f2bce25a0f=T & br:fb1ba40798cf=F
- call `convertUser` line 71 requires: br:0746154f1c47=F & br:af0e24f4367b=F & br:01807a7b80a2=F & br:17f2bce25a0f=F

### gapi.validateUpdateUserRequest  (gapi/rpc_update_user.go)
- site br:57793335771a line 77: `err != nil` | operands: err ← call:req.GetUsername, call:val.ValidateUsername, global:val, param:req | requires: — | then exits: False, else exits: False
- site br:444b7eee95f8 line 81: `req.Password != nil` | operands: req.Password ← param:req.Password | requires: — | then exits: False, else exits: False
- site br:d827424c3b5f line 82: `err != nil` | operands: err ← call:req.GetPassword, call:val.ValidatePassword, global:val, param:req | requires: br:444b7eee95f8=T | then exits: False, else exits: False
- site br:578b58ceb4d3 line 87: `req.FullName != nil` | operands: req.FullName ← param:req.FullName | requires: — | then exits: False, else exits: False
- site br:864c3600c3d5 line 88: `err != nil` | operands: err ← call:req.GetFullName, call:val.ValidateFullName, global:val, param:req | requires: br:578b58ceb4d3=T | then exits: False, else exits: False
- site br:9558e38bf1ec line 93: `req.Email != nil` | operands: req.Email ← param:req.Email | requires: — | then exits: False, else exits: False
- site br:f63e639d4185 line 94: `err != nil` | operands: err ← call:req.GetEmail, call:val.ValidateEmail, global:val, param:req | requires: br:9558e38bf1ec=T | then exits: False, else exits: False
- call `req.GetUsername` line 77 requires: —
- call `val.ValidateUsername` line 77 requires: —
- call `fieldViolation` line 78 requires: br:57793335771a=T
- call `append` line 78 requires: br:57793335771a=T
- call `req.GetPassword` line 82 requires: br:444b7eee95f8=T
- call `val.ValidatePassword` line 82 requires: br:444b7eee95f8=T
- call `fieldViolation` line 83 requires: br:444b7eee95f8=T & br:d827424c3b5f=T
- call `append` line 83 requires: br:444b7eee95f8=T & br:d827424c3b5f=T
- call `req.GetFullName` line 88 requires: br:578b58ceb4d3=T
- call `val.ValidateFullName` line 88 requires: br:578b58ceb4d3=T
- call `fieldViolation` line 89 requires: br:578b58ceb4d3=T & br:864c3600c3d5=T
- call `append` line 89 requires: br:578b58ceb4d3=T & br:864c3600c3d5=T
- call `req.GetEmail` line 94 requires: br:9558e38bf1ec=T
- call `val.ValidateEmail` line 94 requires: br:9558e38bf1ec=T
- call `fieldViolation` line 95 requires: br:9558e38bf1ec=T & br:f63e639d4185=T
- call `append` line 95 requires: br:9558e38bf1ec=T & br:f63e639d4185=T

### token.PasetoMaker.CreateToken  (token/paseto_maker.go)
- site br:0713394c9923 line 34: `err != nil` | operands: err ← call:NewPayload#1 | requires: — | then exits: True, else exits: False
- call `NewPayload` line 33 requires: —
- call `maker.paseto.Encrypt` line 38 requires: br:0713394c9923=F

### token.PasetoMaker.VerifyToken  (token/paseto_maker.go)
- site br:0607e4d952f6 line 47: `err != nil` | operands: err ← call:maker.paseto.Decrypt | requires: — | then exits: True, else exits: False
- site br:c7d403dfabc3 line 52: `err != nil` | operands: err ← call:payload.Valid | requires: br:0607e4d952f6=F | then exits: True, else exits: False
- call `maker.paseto.Decrypt` line 46 requires: —
- call `payload.Valid` line 51 requires: br:0607e4d952f6=F

### token.NewPayload  (token/payload.go)
- site br:b4114c26b15a line 28: `err != nil` | operands: err ← call:uuid.NewRandom#1 | requires: — | then exits: True, else exits: False
- call `uuid.NewRandom` line 27 requires: —
- call `time.Now` line 36 requires: br:b4114c26b15a=F
- call `time.Now` line 37 requires: br:b4114c26b15a=F
- call `time.Now().Add` line 37 requires: br:b4114c26b15a=F

### token.Payload.Valid  (token/payload.go)
- site br:28f7c30a7189 line 44: `time.Now().After(payload.ExpiredAt)` | operands: time ← global:time; payload.ExpiredAt ← param:payload.ExpiredAt | requires: — | then exits: True, else exits: False
- call `time.Now` line 44 requires: —
- call `time.Now().After` line 44 requires: —

## Observed event logs (shown tests, at head)

Calls of the listed functions in chronological order, indented by depth among them (everything else is looked through), with argument shapes and value digests, results, exits, and the observed outcome of every decision site evaluated in those calls.

```
### InvalidEmail  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error
call token.PasetoMaker.CreateToken(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
  call token.NewPayload(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#60d1da) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#af0da0) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid() [returned] -> #5da3a4
        branch br:28f7c30a7189 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#60d1da) [returned] -> #0dd246
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = T
  branch br:af0e24f4367b `violations != nil` = T

### NoAuthorization  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error
call gapi.Server.UpdateUser(ctx=context.backgroundCtx#2e2a50, req=*pb.UpdateUserRequest#134c96) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=context.backgroundCtx#2e2a50, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = T
  branch br:0746154f1c47 `err != nil` = T

### OK  test: passed  exits: gapi.Server.UpdateUser returned
call token.PasetoMaker.CreateToken(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
  call token.NewPayload(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#134c96) [returned]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#36d444) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid() [returned] -> #5da3a4
        branch br:28f7c30a7189 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  call db/sqlc.Queries.UpdateUser(arg0=*context.valueCtx, arg1=db.UpdateUserParams#bf744c) [returned] (stand-in, mocked)
  branch br:17f2bce25a0f `err != nil` = F
  call gapi.convertUser(user=db.User#c38c92) [returned]

### OtherDepositorCannotUpdateThisUserInfo  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error
call token.PasetoMaker.CreateToken(username=string#616c4a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
  call token.NewPayload(username=string#616c4a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#134c96) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#24dc50) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid() [returned] -> #5da3a4
        branch br:28f7c30a7189 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = T

### UserNotFound  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error
call token.PasetoMaker.CreateToken(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
  call token.NewPayload(username=string#26b18a, role=string#2ab61d, duration=time.Duration#f5e4f3) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#134c96) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#0822ac) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid() [returned] -> #5da3a4
        branch br:28f7c30a7189 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  call db/sqlc.Queries.UpdateUser(arg0=*context.valueCtx, arg1=db.UpdateUserParams#bf744c) [returned-error:go:*errors.errorString] (stand-in, mocked)
  branch br:17f2bce25a0f `err != nil` = T
  branch br:fb1ba40798cf `errors.Is(err, db.ErrRecordNotFound)` = T
```

Withheld (observed, not shown): BankerCanUpdateUserInfo, ExpiredToken

## The change (git diff 6e267986..2e2094e2, non-test Go sources in gapi, token, util, api)

```diff
diff --git a/api/token.go b/api/token.go
index 924ffd4..7d7b615 100644
--- a/api/token.go
+++ b/api/token.go
@@ -68,6 +68,7 @@ func (server *Server) renewAccessToken(ctx *gin.Context) {
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		refreshPayload.Username,
+		refreshPayload.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
diff --git a/api/user.go b/api/user.go
index 65ce1a5..94de476 100644
--- a/api/user.go
+++ b/api/user.go
@@ -109,6 +109,7 @@ func (server *Server) loginUser(ctx *gin.Context) {
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
@@ -118,6 +119,7 @@ func (server *Server) loginUser(ctx *gin.Context) {
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.RefreshTokenDuration,
 	)
 	if err != nil {
diff --git a/gapi/authorization.go b/gapi/authorization.go
index e7e5583..892467d 100644
--- a/gapi/authorization.go
+++ b/gapi/authorization.go
@@ -14,7 +14,7 @@ const (
 	authorizationBearer = "bearer"
 )
 
-func (server *Server) authorizeUser(ctx context.Context) (*token.Payload, error) {
+func (server *Server) authorizeUser(ctx context.Context, accessibleRoles []string) (*token.Payload, error) {
 	md, ok := metadata.FromIncomingContext(ctx)
 	if !ok {
 		return nil, fmt.Errorf("missing metadata")
@@ -42,5 +42,18 @@ func (server *Server) authorizeUser(ctx context.Context) (*token.Payload, error)
 		return nil, fmt.Errorf("invalid access token: %s", err)
 	}
 
+	if !hasPermission(payload.Role, accessibleRoles) {
+		return nil, fmt.Errorf("permission denied")
+	}
+
 	return payload, nil
 }
+
+func hasPermission(userRole string, accessibleRoles []string) bool {
+	for _, role := range accessibleRoles {
+		if userRole == role {
+			return true
+		}
+	}
+	return false
+}
diff --git a/gapi/rpc_login_user.go b/gapi/rpc_login_user.go
index 5a1b045..259ba21 100644
--- a/gapi/rpc_login_user.go
+++ b/gapi/rpc_login_user.go
@@ -35,6 +35,7 @@ func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
@@ -43,6 +44,7 @@ func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.RefreshTokenDuration,
 	)
 	if err != nil {
diff --git a/gapi/rpc_update_user.go b/gapi/rpc_update_user.go
index 2b5ef8d..2a290cd 100644
--- a/gapi/rpc_update_user.go
+++ b/gapi/rpc_update_user.go
@@ -16,7 +16,7 @@ import (
 )
 
 func (server *Server) UpdateUser(ctx context.Context, req *pb.UpdateUserRequest) (*pb.UpdateUserResponse, error) {
-	authPayload, err := server.authorizeUser(ctx)
+	authPayload, err := server.authorizeUser(ctx, []string{util.BankerRole, util.DepositorRole})
 	if err != nil {
 		return nil, unauthenticatedError(err)
 	}
@@ -26,7 +26,7 @@ func (server *Server) UpdateUser(ctx context.Context, req *pb.UpdateUserRequest)
 		return nil, invalidArgumentError(violations)
 	}
 
-	if authPayload.Username != req.GetUsername() {
+	if authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername() {
 		return nil, status.Errorf(codes.PermissionDenied, "cannot update other user's info")
 	}
 
diff --git a/token/jwt_maker.go b/token/jwt_maker.go
index 2df8f2a..02d7cdd 100644
--- a/token/jwt_maker.go
+++ b/token/jwt_maker.go
@@ -24,8 +24,8 @@ func NewJWTMaker(secretKey string) (Maker, error) {
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *JWTMaker) CreateToken(username string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, duration)
+func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration)
 	if err != nil {
 		return "", payload, err
 	}
diff --git a/token/maker.go b/token/maker.go
index 2228d05..9466e78 100644
--- a/token/maker.go
+++ b/token/maker.go
@@ -7,7 +7,7 @@ import (
 // Maker is an interface for managing tokens
 type Maker interface {
 	// CreateToken creates a new token for a specific username and duration
-	CreateToken(username string, duration time.Duration) (string, *Payload, error)
+	CreateToken(username string, role string, duration time.Duration) (string, *Payload, error)
 
 	// VerifyToken checks if the token is valid or not
 	VerifyToken(token string) (*Payload, error)
diff --git a/token/paseto_maker.go b/token/paseto_maker.go
index 0f63d5e..d855837 100644
--- a/token/paseto_maker.go
+++ b/token/paseto_maker.go
@@ -29,8 +29,8 @@ func NewPasetoMaker(symmetricKey string) (Maker, error) {
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *PasetoMaker) CreateToken(username string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, duration)
+func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration)
 	if err != nil {
 		return "", payload, err
 	}
diff --git a/token/payload.go b/token/payload.go
index 9645a55..dccae11 100644
--- a/token/payload.go
+++ b/token/payload.go
@@ -17,12 +17,13 @@ var (
 type Payload struct {
 	ID        uuid.UUID `json:"id"`
 	Username  string    `json:"username"`
+	Role      string    `json:"role"`
 	IssuedAt  time.Time `json:"issued_at"`
 	ExpiredAt time.Time `json:"expired_at"`
 }
 
 // NewPayload creates a new token payload with a specific username and duration
-func NewPayload(username string, duration time.Duration) (*Payload, error) {
+func NewPayload(username string, role string, duration time.Duration) (*Payload, error) {
 	tokenID, err := uuid.NewRandom()
 	if err != nil {
 		return nil, err
@@ -31,6 +32,7 @@ func NewPayload(username string, duration time.Duration) (*Payload, error) {
 	payload := &Payload{
 		ID:        tokenID,
 		Username:  username,
+		Role:      role,
 		IssuedAt:  time.Now(),
 		ExpiredAt: time.Now().Add(duration),
 	}
diff --git a/util/role.go b/util/role.go
new file mode 100644
index 0000000..d311fff
--- /dev/null
+++ b/util/role.go
@@ -0,0 +1,6 @@
+package util
+
+const (
+	DepositorRole = "depositor"
+	BankerRole    = "banker"
+)
```

## Source at HEAD: gapi/authorization.go

```go
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"fmt"
   6  	"strings"
   7  
   8  	"github.com/techschool/simplebank/token"
   9  	"google.golang.org/grpc/metadata"
  10  )
  11  
  12  const (
  13  	authorizationHeader = "authorization"
  14  	authorizationBearer = "bearer"
  15  )
  16  
  17  func (server *Server) authorizeUser(ctx context.Context, accessibleRoles []string) (*token.Payload, error) {
  18  	md, ok := metadata.FromIncomingContext(ctx)
  19  	if !ok {
  20  		return nil, fmt.Errorf("missing metadata")
  21  	}
  22  
  23  	values := md.Get(authorizationHeader)
  24  	if len(values) == 0 {
  25  		return nil, fmt.Errorf("missing authorization header")
  26  	}
  27  
  28  	authHeader := values[0]
  29  	fields := strings.Fields(authHeader)
  30  	if len(fields) < 2 {
  31  		return nil, fmt.Errorf("invalid authorization header format")
  32  	}
  33  
  34  	authType := strings.ToLower(fields[0])
  35  	if authType != authorizationBearer {
  36  		return nil, fmt.Errorf("unsupported authorization type: %s", authType)
  37  	}
  38  
  39  	accessToken := fields[1]
  40  	payload, err := server.tokenMaker.VerifyToken(accessToken)
  41  	if err != nil {
  42  		return nil, fmt.Errorf("invalid access token: %s", err)
  43  	}
  44  
  45  	if !hasPermission(payload.Role, accessibleRoles) {
  46  		return nil, fmt.Errorf("permission denied")
  47  	}
  48  
  49  	return payload, nil
  50  }
  51  
  52  func hasPermission(userRole string, accessibleRoles []string) bool {
  53  	for _, role := range accessibleRoles {
  54  		if userRole == role {
  55  			return true
  56  		}
  57  	}
  58  	return false
  59  }
```

## Source at HEAD: gapi/rpc_update_user.go

```go
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"errors"
   6  	"time"
   7  
   8  	"github.com/jackc/pgx/v5/pgtype"
   9  	db "github.com/techschool/simplebank/db/sqlc"
  10  	"github.com/techschool/simplebank/pb"
  11  	"github.com/techschool/simplebank/util"
  12  	"github.com/techschool/simplebank/val"
  13  	"google.golang.org/genproto/googleapis/rpc/errdetails"
  14  	"google.golang.org/grpc/codes"
  15  	"google.golang.org/grpc/status"
  16  )
  17  
  18  func (server *Server) UpdateUser(ctx context.Context, req *pb.UpdateUserRequest) (*pb.UpdateUserResponse, error) {
  19  	authPayload, err := server.authorizeUser(ctx, []string{util.BankerRole, util.DepositorRole})
  20  	if err != nil {
  21  		return nil, unauthenticatedError(err)
  22  	}
  23  
  24  	violations := validateUpdateUserRequest(req)
  25  	if violations != nil {
  26  		return nil, invalidArgumentError(violations)
  27  	}
  28  
  29  	if authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername() {
  30  		return nil, status.Errorf(codes.PermissionDenied, "cannot update other user's info")
  31  	}
  32  
  33  	arg := db.UpdateUserParams{
  34  		Username: req.GetUsername(),
  35  		FullName: pgtype.Text{
  36  			String: req.GetFullName(),
  37  			Valid:  req.FullName != nil,
  38  		},
  39  		Email: pgtype.Text{
  40  			String: req.GetEmail(),
  41  			Valid:  req.Email != nil,
  42  		},
  43  	}
  44  
  45  	if req.Password != nil {
  46  		hashedPassword, err := util.HashPassword(req.GetPassword())
  47  		if err != nil {
  48  			return nil, status.Errorf(codes.Internal, "failed to hash password: %s", err)
  49  		}
  50  
  51  		arg.HashedPassword = pgtype.Text{
  52  			String: hashedPassword,
  53  			Valid:  true,
  54  		}
  55  
  56  		arg.PasswordChangedAt = pgtype.Timestamptz{
  57  			Time:  time.Now(),
  58  			Valid: true,
  59  		}
  60  	}
  61  
  62  	user, err := server.store.UpdateUser(ctx, arg)
  63  	if err != nil {
  64  		if errors.Is(err, db.ErrRecordNotFound) {
  65  			return nil, status.Errorf(codes.NotFound, "user not found")
  66  		}
  67  		return nil, status.Errorf(codes.Internal, "failed to update user: %s", err)
  68  	}
  69  
  70  	rsp := &pb.UpdateUserResponse{
  71  		User: convertUser(user),
  72  	}
  73  	return rsp, nil
  74  }
  75  
  76  func validateUpdateUserRequest(req *pb.UpdateUserRequest) (violations []*errdetails.BadRequest_FieldViolation) {
  77  	if err := val.ValidateUsername(req.GetUsername()); err != nil {
  78  		violations = append(violations, fieldViolation("username", err))
  79  	}
  80  
  81  	if req.Password != nil {
  82  		if err := val.ValidatePassword(req.GetPassword()); err != nil {
  83  			violations = append(violations, fieldViolation("password", err))
  84  		}
  85  	}
  86  
  87  	if req.FullName != nil {
  88  		if err := val.ValidateFullName(req.GetFullName()); err != nil {
  89  			violations = append(violations, fieldViolation("full_name", err))
  90  		}
  91  	}
  92  
  93  	if req.Email != nil {
  94  		if err := val.ValidateEmail(req.GetEmail()); err != nil {
  95  			violations = append(violations, fieldViolation("email", err))
  96  		}
  97  	}
  98  
  99  	return violations
 100  }
```

## Source at HEAD: token/payload.go

```go
   1  package token
   2  
   3  import (
   4  	"errors"
   5  	"time"
   6  
   7  	"github.com/google/uuid"
   8  )
   9  
  10  // Different types of error returned by the VerifyToken function
  11  var (
  12  	ErrInvalidToken = errors.New("token is invalid")
  13  	ErrExpiredToken = errors.New("token has expired")
  14  )
  15  
  16  // Payload contains the payload data of the token
  17  type Payload struct {
  18  	ID        uuid.UUID `json:"id"`
  19  	Username  string    `json:"username"`
  20  	Role      string    `json:"role"`
  21  	IssuedAt  time.Time `json:"issued_at"`
  22  	ExpiredAt time.Time `json:"expired_at"`
  23  }
  24  
  25  // NewPayload creates a new token payload with a specific username and duration
  26  func NewPayload(username string, role string, duration time.Duration) (*Payload, error) {
  27  	tokenID, err := uuid.NewRandom()
  28  	if err != nil {
  29  		return nil, err
  30  	}
  31  
  32  	payload := &Payload{
  33  		ID:        tokenID,
  34  		Username:  username,
  35  		Role:      role,
  36  		IssuedAt:  time.Now(),
  37  		ExpiredAt: time.Now().Add(duration),
  38  	}
  39  	return payload, nil
  40  }
  41  
  42  // Valid checks if the token payload is valid or not
  43  func (payload *Payload) Valid() error {
  44  	if time.Now().After(payload.ExpiredAt) {
  45  		return ErrExpiredToken
  46  	}
  47  	return nil
  48  }
```

## Source at HEAD: token/paseto_maker.go

```go
   1  package token
   2  
   3  import (
   4  	"fmt"
   5  	"time"
   6  
   7  	"github.com/aead/chacha20poly1305"
   8  	"github.com/o1egl/paseto"
   9  )
  10  
  11  // PasetoMaker is a PASETO token maker
  12  type PasetoMaker struct {
  13  	paseto       *paseto.V2
  14  	symmetricKey []byte
  15  }
  16  
  17  // NewPasetoMaker creates a new PasetoMaker
  18  func NewPasetoMaker(symmetricKey string) (Maker, error) {
  19  	if len(symmetricKey) != chacha20poly1305.KeySize {
  20  		return nil, fmt.Errorf("invalid key size: must be exactly %d characters", chacha20poly1305.KeySize)
  21  	}
  22  
  23  	maker := &PasetoMaker{
  24  		paseto:       paseto.NewV2(),
  25  		symmetricKey: []byte(symmetricKey),
  26  	}
  27  
  28  	return maker, nil
  29  }
  30  
  31  // CreateToken creates a new token for a specific username and duration
  32  func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
  33  	payload, err := NewPayload(username, role, duration)
  34  	if err != nil {
  35  		return "", payload, err
  36  	}
  37  
  38  	token, err := maker.paseto.Encrypt(maker.symmetricKey, payload, nil)
  39  	return token, payload, err
  40  }
  41  
  42  // VerifyToken checks if the token is valid or not
  43  func (maker *PasetoMaker) VerifyToken(token string) (*Payload, error) {
  44  	payload := &Payload{}
  45  
  46  	err := maker.paseto.Decrypt(token, maker.symmetricKey, payload, nil)
  47  	if err != nil {
  48  		return nil, ErrInvalidToken
  49  	}
  50  
  51  	err = payload.Valid()
  52  	if err != nil {
  53  		return nil, err
  54  	}
  55  
  56  	return payload, nil
  57  }
```

## Source at HEAD: util/role.go

```go
   1  package util
   2  
   3  const (
   4  	DepositorRole = "depositor"
   5  	BankerRole    = "banker"
   6  )
```

## Source at HEAD: gapi/rpc_update_user_test.go

```go
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"testing"
   6  	"time"
   7  
   8  	"github.com/golang/mock/gomock"
   9  	"github.com/jackc/pgx/v5/pgtype"
  10  	"github.com/stretchr/testify/require"
  11  	mockdb "github.com/techschool/simplebank/db/mock"
  12  	db "github.com/techschool/simplebank/db/sqlc"
  13  	"github.com/techschool/simplebank/pb"
  14  	"github.com/techschool/simplebank/token"
  15  	"github.com/techschool/simplebank/util"
  16  	"google.golang.org/grpc/codes"
  17  	"google.golang.org/grpc/status"
  18  )
  19  
  20  func TestUpdateUserAPI(t *testing.T) {
  21  	user, _ := randomUser(t, util.DepositorRole)
  22  	other, _ := randomUser(t, util.DepositorRole)
  23  	banker, _ := randomUser(t, util.BankerRole)
  24  
  25  	newName := util.RandomOwner()
  26  	newEmail := util.RandomEmail()
  27  	invalidEmail := "invalid-email"
  28  
  29  	testCases := []struct {
  30  		name          string
  31  		req           *pb.UpdateUserRequest
  32  		buildStubs    func(store *mockdb.MockStore)
  33  		buildContext  func(t *testing.T, tokenMaker token.Maker) context.Context
  34  		checkResponse func(t *testing.T, res *pb.UpdateUserResponse, err error)
  35  	}{
  36  		{
  37  			name: "OK",
  38  			req: &pb.UpdateUserRequest{
  39  				Username: user.Username,
  40  				FullName: &newName,
  41  				Email:    &newEmail,
  42  			},
  43  			buildStubs: func(store *mockdb.MockStore) {
  44  				arg := db.UpdateUserParams{
  45  					Username: user.Username,
  46  					FullName: pgtype.Text{
  47  						String: newName,
  48  						Valid:  true,
  49  					},
  50  					Email: pgtype.Text{
  51  						String: newEmail,
  52  						Valid:  true,
  53  					},
  54  				}
  55  				updatedUser := db.User{
  56  					Username:          user.Username,
  57  					HashedPassword:    user.HashedPassword,
  58  					FullName:          newName,
  59  					Email:             newEmail,
  60  					PasswordChangedAt: user.PasswordChangedAt,
  61  					CreatedAt:         user.CreatedAt,
  62  					IsEmailVerified:   user.IsEmailVerified,
  63  				}
  64  				store.EXPECT().
  65  					UpdateUser(gomock.Any(), gomock.Eq(arg)).
  66  					Times(1).
  67  					Return(updatedUser, nil)
  68  			},
  69  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
  70  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute)
  71  			},
  72  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
  73  				require.NoError(t, err)
  74  				require.NotNil(t, res)
  75  				updatedUser := res.GetUser()
  76  				require.Equal(t, user.Username, updatedUser.Username)
  77  				require.Equal(t, newName, updatedUser.FullName)
  78  				require.Equal(t, newEmail, updatedUser.Email)
  79  			},
  80  		},
  81  		{
  82  			name: "BankerCanUpdateUserInfo",
  83  			req: &pb.UpdateUserRequest{
  84  				Username: user.Username,
  85  				FullName: &newName,
  86  				Email:    &newEmail,
  87  			},
  88  			buildStubs: func(store *mockdb.MockStore) {
  89  				arg := db.UpdateUserParams{
  90  					Username: user.Username,
  91  					FullName: pgtype.Text{
  92  						String: newName,
  93  						Valid:  true,
  94  					},
  95  					Email: pgtype.Text{
  96  						String: newEmail,
  97  						Valid:  true,
  98  					},
  99  				}
 100  				updatedUser := db.User{
 101  					Username:          user.Username,
 102  					HashedPassword:    user.HashedPassword,
 103  					FullName:          newName,
 104  					Email:             newEmail,
 105  					PasswordChangedAt: user.PasswordChangedAt,
 106  					CreatedAt:         user.CreatedAt,
 107  					IsEmailVerified:   user.IsEmailVerified,
 108  				}
 109  				store.EXPECT().
 110  					UpdateUser(gomock.Any(), gomock.Eq(arg)).
 111  					Times(1).
 112  					Return(updatedUser, nil)
 113  			},
 114  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 115  				return newContextWithBearerToken(t, tokenMaker, banker.Username, banker.Role, time.Minute)
 116  			},
 117  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 118  				require.NoError(t, err)
 119  				require.NotNil(t, res)
 120  				updatedUser := res.GetUser()
 121  				require.Equal(t, user.Username, updatedUser.Username)
 122  				require.Equal(t, newName, updatedUser.FullName)
 123  				require.Equal(t, newEmail, updatedUser.Email)
 124  			},
 125  		},
 126  		{
 127  			name: "OtherDepositorCannotUpdateThisUserInfo",
 128  			req: &pb.UpdateUserRequest{
 129  				Username: user.Username,
 130  				FullName: &newName,
 131  				Email:    &newEmail,
 132  			},
 133  			buildStubs: func(store *mockdb.MockStore) {
 134  				store.EXPECT().
 135  					UpdateUser(gomock.Any(), gomock.Any()).
 136  					Times(0)
 137  			},
 138  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 139  				return newContextWithBearerToken(t, tokenMaker, other.Username, other.Role, time.Minute)
 140  			},
 141  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 142  				require.Error(t, err)
 143  				st, ok := status.FromError(err)
 144  				require.True(t, ok)
 145  				require.Equal(t, codes.PermissionDenied, st.Code())
 146  			},
 147  		},
 148  		{
 149  			name: "UserNotFound",
 150  			req: &pb.UpdateUserRequest{
 151  				Username: user.Username,
 152  				FullName: &newName,
 153  				Email:    &newEmail,
 154  			},
 155  			buildStubs: func(store *mockdb.MockStore) {
 156  				store.EXPECT().
 157  					UpdateUser(gomock.Any(), gomock.Any()).
 158  					Times(1).
 159  					Return(db.User{}, db.ErrRecordNotFound)
 160  			},
 161  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 162  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute)
 163  			},
 164  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 165  				require.Error(t, err)
 166  				st, ok := status.FromError(err)
 167  				require.True(t, ok)
 168  				require.Equal(t, codes.NotFound, st.Code())
 169  			},
 170  		},
 171  		{
 172  			name: "InvalidEmail",
 173  			req: &pb.UpdateUserRequest{
 174  				Username: user.Username,
 175  				FullName: &newName,
 176  				Email:    &invalidEmail,
 177  			},
 178  			buildStubs: func(store *mockdb.MockStore) {
 179  				store.EXPECT().
 180  					UpdateUser(gomock.Any(), gomock.Any()).
 181  					Times(0)
 182  			},
 183  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 184  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute)
 185  			},
 186  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 187  				require.Error(t, err)
 188  				st, ok := status.FromError(err)
 189  				require.True(t, ok)
 190  				require.Equal(t, codes.InvalidArgument, st.Code())
 191  			},
 192  		},
 193  		{
 194  			name: "ExpiredToken",
 195  			req: &pb.UpdateUserRequest{
 196  				Username: user.Username,
 197  				FullName: &newName,
 198  				Email:    &newEmail,
 199  			},
 200  			buildStubs: func(store *mockdb.MockStore) {
 201  				store.EXPECT().
 202  					UpdateUser(gomock.Any(), gomock.Any()).
 203  					Times(0)
 204  			},
 205  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 206  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, -time.Minute)
 207  			},
 208  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 209  				require.Error(t, err)
 210  				st, ok := status.FromError(err)
 211  				require.True(t, ok)
 212  				require.Equal(t, codes.Unauthenticated, st.Code())
 213  			},
 214  		},
 215  		{
 216  			name: "NoAuthorization",
 217  			req: &pb.UpdateUserRequest{
 218  				Username: user.Username,
 219  				FullName: &newName,
 220  				Email:    &newEmail,
 221  			},
 222  			buildStubs: func(store *mockdb.MockStore) {
 223  				store.EXPECT().
 224  					UpdateUser(gomock.Any(), gomock.Any()).
 225  					Times(0)
 226  			},
 227  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 228  				return context.Background()
 229  			},
 230  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 231  				require.Error(t, err)
 232  				st, ok := status.FromError(err)
 233  				require.True(t, ok)
 234  				require.Equal(t, codes.Unauthenticated, st.Code())
 235  			},
 236  		},
 237  	}
 238  
 239  	for i := range testCases {
 240  		tc := testCases[i]
 241  
 242  		t.Run(tc.name, func(t *testing.T) {
 243  			storeCtrl := gomock.NewController(t)
 244  			defer storeCtrl.Finish()
 245  			store := mockdb.NewMockStore(storeCtrl)
 246  
 247  			tc.buildStubs(store)
 248  			server := newTestServer(t, store, nil)
 249  
 250  			ctx := tc.buildContext(t, server.tokenMaker)
 251  			res, err := server.UpdateUser(ctx, tc.req)
 252  			tc.checkResponse(t, res, err)
 253  		})
 254  	}
 255  }
```

## Source at HEAD: gapi/main_test.go

```go
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"fmt"
   6  	"testing"
   7  	"time"
   8  
   9  	"github.com/stretchr/testify/require"
  10  	db "github.com/techschool/simplebank/db/sqlc"
  11  	"github.com/techschool/simplebank/token"
  12  	"github.com/techschool/simplebank/util"
  13  	"github.com/techschool/simplebank/worker"
  14  	"google.golang.org/grpc/metadata"
  15  )
  16  
  17  func newTestServer(t *testing.T, store db.Store, taskDistributor worker.TaskDistributor) *Server {
  18  	config := util.Config{
  19  		TokenSymmetricKey:   util.RandomString(32),
  20  		AccessTokenDuration: time.Minute,
  21  	}
  22  
  23  	server, err := NewServer(config, store, taskDistributor)
  24  	require.NoError(t, err)
  25  
  26  	return server
  27  }
  28  
  29  func newContextWithBearerToken(t *testing.T, tokenMaker token.Maker, username string, role string, duration time.Duration) context.Context {
  30  	accessToken, _, err := tokenMaker.CreateToken(username, role, duration)
  31  	require.NoError(t, err)
  32  
  33  	bearerToken := fmt.Sprintf("%s %s", authorizationBearer, accessToken)
  34  	md := metadata.MD{
  35  		authorizationHeader: []string{
  36  			bearerToken,
  37  		},
  38  	}
  39  
  40  	return metadata.NewIncomingContext(context.Background(), md)
  41  }
```
