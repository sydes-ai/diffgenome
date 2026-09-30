# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is git diff 6e2679863e4c691db46ec14761a3b3e303e05ce1..2e2094e209a2e9432b53a0d142f52bc8ccce82c2 in the repository simplebank (runtime
go/test). Changed symbols: api.Server.loginUser, api.Server.renewAccessToken, db/sqlc.Queries.CreateUser, db/sqlc.Queries.GetUser, db/sqlc.Queries.UpdateUser, db/sqlc.User, gapi.Server.LoginUser, gapi.Server.UpdateUser, gapi.Server.authorizeUser, gapi.hasPermission, token.JWTMaker.CreateToken, token.Maker, token.NewPayload, token.PasetoMaker.CreateToken, token.Payload.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- decision sites (`if`) with stable ids `br:...`, source predicate, operand origins (local
  def-use), and the (site, outcome) pairs required to reach them;
- for every call and store: which (site, outcome) pairs it requires;
- for the tests: the ordered event log of the relevant calls, each call's argument shapes with
  value digests (`#abcd12`: equal digests = equal values; contents are not recorded), results,
  every call's observed EXIT, and the observed outcome (T/F) of every decision site in those
  calls. The digest `#5da3a4` is Go's `nil`.

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior (which calls happen, which decisions go which way,
how each entry call exits). A machine checks everything you cite and assigns status; you assign
none. Write a scenario for every test listed, keyed by its exact test id as written in the
event logs; each is predicted from your genome and compared with what executed.

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



## Required sites

Every OBSERVED evaluation of these sites is scored, in every test.

- br:9c4f387be39d go:api.Server.loginUser line 89: `err != nil`   (not evaluated by any test)
- br:365f01cfaf9a go:api.Server.loginUser line 95: `err != nil`   (not evaluated by any test)
- br:8c4975b74bce go:api.Server.loginUser line 96: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated by any test)
- br:67ea910da26c go:api.Server.loginUser line 105: `err != nil`   (not evaluated by any test)
- br:620e5470e915 go:api.Server.loginUser line 115: `err != nil`   (not evaluated by any test)
- br:f256c2c9ce95 go:api.Server.loginUser line 125: `err != nil`   (not evaluated by any test)
- br:31f8086bdd5e go:api.Server.loginUser line 139: `err != nil`   (not evaluated by any test)
- br:7f4a03494e61 go:api.Server.renewAccessToken line 24: `err != nil`   (not evaluated by any test)
- br:8a53d4418573 go:api.Server.renewAccessToken line 30: `err != nil`   (not evaluated by any test)
- br:c25e0917e397 go:api.Server.renewAccessToken line 36: `err != nil`   (not evaluated by any test)
- br:03efe4cada2e go:api.Server.renewAccessToken line 37: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated by any test)
- br:eca7bb637933 go:api.Server.renewAccessToken line 45: `session.IsBlocked`   (not evaluated by any test)
- br:0cb1367c07fc go:api.Server.renewAccessToken line 51: `session.Username != refreshPayload.Username`   (not evaluated by any test)
- br:f2bc1697337d go:api.Server.renewAccessToken line 57: `session.RefreshToken != req.RefreshToken`   (not evaluated by any test)
- br:0f24bd276232 go:api.Server.renewAccessToken line 63: `time.Now().After(session.ExpiresAt)`   (not evaluated by any test)
- br:ce6bba1a95f1 go:api.Server.renewAccessToken line 74: `err != nil`   (not evaluated by any test)
- br:930116d7ba7e go:gapi.Server.LoginUser line 19: `violations != nil`   (not evaluated by any test)
- br:8766f154fd07 go:gapi.Server.LoginUser line 24: `err != nil`   (not evaluated by any test)
- br:aa1290a8b57d go:gapi.Server.LoginUser line 25: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated by any test)
- br:fd4e92e7cbac go:gapi.Server.LoginUser line 32: `err != nil`   (not evaluated by any test)
- br:f3feb339909f go:gapi.Server.LoginUser line 41: `err != nil`   (not evaluated by any test)
- br:4ec58fbc60ce go:gapi.Server.LoginUser line 50: `err != nil`   (not evaluated by any test)
- br:484cec688a66 go:gapi.Server.LoginUser line 64: `err != nil`   (not evaluated by any test)
- br:0746154f1c47 go:gapi.Server.UpdateUser line 20: `err != nil`
- br:af0e24f4367b go:gapi.Server.UpdateUser line 25: `violations != nil`
- br:01807a7b80a2 go:gapi.Server.UpdateUser line 29: `authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`
- br:815be3bfb43a go:gapi.Server.UpdateUser line 45: `req.Password != nil`
- br:5f17958f3d3f go:gapi.Server.UpdateUser line 47: `err != nil`   (not evaluated by any test)
- br:17f2bce25a0f go:gapi.Server.UpdateUser line 63: `err != nil`
- br:fb1ba40798cf go:gapi.Server.UpdateUser line 64: `errors.Is(err, db.ErrRecordNotFound)`
- br:e3505bc4c4b9 go:gapi.Server.authorizeUser line 19: `!ok`
- br:a572eeb6a4c8 go:gapi.Server.authorizeUser line 24: `len(values) == 0`
- br:4393757b65d7 go:gapi.Server.authorizeUser line 30: `len(fields) < 2`
- br:2e2f712d6301 go:gapi.Server.authorizeUser line 35: `authType != authorizationBearer`
- br:c71158777bce go:gapi.Server.authorizeUser line 41: `err != nil`
- br:c1bc39962889 go:gapi.Server.authorizeUser line 45: `!hasPermission(payload.Role, accessibleRoles)`
- br:92f48828a554 go:gapi.hasPermission line 54: `userRole == role`
- br:d9f1e0c214f9 go:token.JWTMaker.CreateToken line 29: `err != nil`   (not evaluated by any test)
- br:b4114c26b15a go:token.NewPayload line 28: `err != nil`
- br:0713394c9923 go:token.PasetoMaker.CreateToken line 34: `err != nil`

## Observed execution structure (deterministic)

```
(from 7 shown execution(s))
- go:gapi.Server.UpdateUser: 7 occurrence(s)
    nearest modeled caller: <root> (in 7 exec)
    runs during: <root> (in 7 exec)
- go:gapi.Server.authorizeUser: 7 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 7 exec)
    runs during: go:gapi.Server.UpdateUser (in 7 exec)
- go:gapi.convertUser: 2 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 2 exec)
    runs during: go:gapi.Server.UpdateUser (in 2 exec)
- go:gapi.hasPermission: 5 occurrence(s)
    nearest modeled caller: go:gapi.Server.authorizeUser (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec), go:gapi.Server.authorizeUser (in 5 exec)
- go:gapi.invalidArgumentError: 1 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 1 exec)
    runs during: go:gapi.Server.UpdateUser (in 1 exec)
- go:gapi.unauthenticatedError: 2 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 2 exec)
    runs during: go:gapi.Server.UpdateUser (in 2 exec)
- go:gapi.validateUpdateUserRequest: 5 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec)
- go:pb.UpdateUserRequest.GetEmail: 8 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 3 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
- go:pb.UpdateUserRequest.GetFullName: 8 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 3 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
- go:pb.UpdateUserRequest.GetUsername: 11 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 4 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec), go:gapi.validateUpdateUserRequest (in 5 exec)
- go:token.NewPayload: 6 occurrence(s)
    nearest modeled caller: go:token.PasetoMaker.CreateToken (in 6 exec)
    runs during: go:token.PasetoMaker.CreateToken (in 6 exec)
- go:token.PasetoMaker.CreateToken: 6 occurrence(s)
    nearest modeled caller: <root> (in 6 exec)
    runs during: <root> (in 6 exec)
- go:token.PasetoMaker.VerifyToken: 6 occurrence(s)
    nearest modeled caller: go:gapi.Server.authorizeUser (in 6 exec)
    runs during: go:gapi.Server.UpdateUser (in 6 exec), go:gapi.Server.authorizeUser (in 6 exec)

inside go:gapi.Server.UpdateUser:
  family go:gapi.Server.authorizeUser: in 7 occurrence(s), once
  family go:gapi.convertUser: in 2 occurrence(s), once
  family go:gapi.invalidArgumentError: in 1 occurrence(s), once
  family go:gapi.unauthenticatedError: in 2 occurrence(s), once
  family go:gapi.validateUpdateUserRequest: in 5 occurrence(s), once
  family go:pb.UpdateUserRequest.GetEmail: in 3 occurrence(s), once
  family go:pb.UpdateUserRequest.GetFullName: in 3 occurrence(s), once
  family go:pb.UpdateUserRequest.GetUsername: in 4 occurrence(s), repeated (up to 2 in one occurrence)
  family site:br:01807a7b80a2: in 4 occurrence(s), once
  family site:br:0746154f1c47: in 7 occurrence(s), once
  family site:br:17f2bce25a0f: in 3 occurrence(s), once
  family site:br:815be3bfb43a: in 3 occurrence(s), once
  family site:br:af0e24f4367b: in 5 occurrence(s), once
  family site:br:fb1ba40798cf: in 1 occurrence(s), once
  go:gapi.Server.authorizeUser BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.invalidArgumentError  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.unauthenticatedError  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:pb.UpdateUserRequest.GetUsername  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:0746154f1c47  (all of the first before all of the second;
      7 occurrence(s), 7 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:gapi.invalidArgumentError  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:pb.UpdateUserRequest.GetUsername  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:pb.UpdateUserRequest.GetEmail BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:pb.UpdateUserRequest.GetEmail BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetEmail BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetEmail BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:01807a7b80a2 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:01807a7b80a2 BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.invalidArgumentError  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.unauthenticatedError  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:0746154f1c47 BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE go:pb.UpdateUserRequest.GetUsername  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0746154f1c47 BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:0746154f1c47 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:0746154f1c47 BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:17f2bce25a0f BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:17f2bce25a0f BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:815be3bfb43a BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:815be3bfb43a BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:815be3bfb43a BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE go:gapi.invalidArgumentError  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE go:pb.UpdateUserRequest.GetUsername  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:af0e24f4367b BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:af0e24f4367b BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  REPEATED REGION: go:pb.UpdateUserRequest.GetUsername, site:br:01807a7b80a2
    (no member starts every repetition: only membership is known)

inside go:gapi.Server.authorizeUser:
  family go:gapi.hasPermission: in 5 occurrence(s), once
  family go:token.PasetoMaker.VerifyToken: in 6 occurrence(s), once
  family site:br:2e2f712d6301: in 6 occurrence(s), once
  family site:br:4393757b65d7: in 6 occurrence(s), once
  family site:br:a572eeb6a4c8: in 6 occurrence(s), once
  family site:br:c1bc39962889: in 5 occurrence(s), once
  family site:br:c71158777bce: in 6 occurrence(s), once
  family site:br:e3505bc4c4b9: in 7 occurrence(s), once
  go:gapi.hasPermission BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c71158777bce  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:2e2f712d6301 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2e2f712d6301 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:4393757b65d7 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:4393757b65d7 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:4393757b65d7 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:c71158777bce BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:c71158777bce BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:a572eeb6a4c8  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))

inside go:gapi.validateUpdateUserRequest:
  family go:pb.UpdateUserRequest.GetEmail: in 5 occurrence(s), once
  family go:pb.UpdateUserRequest.GetFullName: in 5 occurrence(s), once
  family go:pb.UpdateUserRequest.GetUsername: in 5 occurrence(s), once
  family site:br:444b7eee95f8: in 5 occurrence(s), once
  family site:br:57793335771a: in 5 occurrence(s), once
  family site:br:578b58ceb4d3: in 5 occurrence(s), once
  family site:br:864c3600c3d5: in 5 occurrence(s), once
  family site:br:9558e38bf1ec: in 5 occurrence(s), once
  family site:br:f63e639d4185: in 5 occurrence(s), once
  go:pb.UpdateUserRequest.GetEmail BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetFullName BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:444b7eee95f8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:57793335771a  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  go:pb.UpdateUserRequest.GetUsername BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE site:br:444b7eee95f8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:57793335771a BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE go:pb.UpdateUserRequest.GetFullName  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:864c3600c3d5 BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:9558e38bf1ec BEFORE go:pb.UpdateUserRequest.GetEmail  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:9558e38bf1ec BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))

inside go:token.PasetoMaker.CreateToken:
  family go:token.NewPayload: in 6 occurrence(s), once
  family site:br:0713394c9923: in 6 occurrence(s), once
  go:token.NewPayload BEFORE site:br:0713394c9923  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))

inside go:token.PasetoMaker.VerifyToken:
  family site:br:0607e4d952f6: in 6 occurrence(s), once
  family site:br:c7d403dfabc3: in 6 occurrence(s), once
  site:br:0607e4d952f6 BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
```

## Mechanics (deterministic, intra-procedural)

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

### gapi.invalidArgumentError  (gapi/error.go)
- site br:ebc242daf335 line 21: `err != nil` | operands: err ← call:statusInvalid.WithDetails#1 | requires: — | then exits: True, else exits: False
- call `status.New` line 18 requires: —
- call `statusInvalid.WithDetails` line 20 requires: —
- call `statusInvalid.Err` line 22 requires: br:ebc242daf335=T
- call `statusDetails.Err` line 25 requires: br:ebc242daf335=F

### gapi.unauthenticatedError  (gapi/error.go)
- call `status.Errorf` line 29 requires: —

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

### pb.UpdateUserRequest.GetUsername  (pb/rpc_update_user.pb.go)
- site br:5afefe007454 line 67: `x != nil` | operands: x ← param:x | requires: — | then exits: True, else exits: False

### pb.UpdateUserRequest.GetFullName  (pb/rpc_update_user.pb.go)
- site br:5e873717aade line 74: `x != nil && x.FullName != nil` | operands: x ← param:x; x.FullName ← param:x.FullName | requires: — | then exits: True, else exits: False

### pb.UpdateUserRequest.GetEmail  (pb/rpc_update_user.pb.go)
- site br:e041dd12b17a line 81: `x != nil && x.Email != nil` | operands: x ← param:x; x.Email ← param:x.Email | requires: — | then exits: True, else exits: False

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

## Observed event logs

Calls of the listed functions in chronological order, indented by depth among them, with argument shapes and value digests, results, exits, and the observed outcome of every decision site evaluated in those calls.

```
### TestUpdateUserAPI/BankerCanUpdateUserInfo  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned; gapi.Server.authorizeUser returned; gapi.hasPermission returned
call token.PasetoMaker.CreateToken(username=string#c73eaf, role=string#9f99e2, duration=time.Duration#f5e4f3) [returned]
  call token.NewPayload(username=string#c73eaf, role=string#9f99e2, duration=time.Duration#f5e4f3) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#134c96) [returned]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#a97a51) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#9f99e2, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
      branch br:5afefe007454 `x != nil` = T
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
      branch br:5e873717aade `x != nil && x.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
      branch br:e041dd12b17a `x != nil && x.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
    branch br:5e873717aade `x != nil && x.FullName != nil` = T
  call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
    branch br:e041dd12b17a `x != nil && x.Email != nil` = T
  branch br:815be3bfb43a `req.Password != nil` = F
  branch br:17f2bce25a0f `err != nil` = F
  call gapi.convertUser(user=db.User#c38c92) [returned]

### TestUpdateUserAPI/ExpiredToken  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned-error:go:*status.Error; gapi.Server.authorizeUser returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#26b18a, role=string#2ab61d, duration=time.Duration#6efa86) [returned]
  call token.NewPayload(username=string#26b18a, role=string#2ab61d, duration=time.Duration#6efa86) [returned]
    branch br:b4114c26b15a `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#134c96) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#af6854) [returned-error:go:*errors.errorString]
      branch br:0607e4d952f6 `err != nil` = F
      branch br:c7d403dfabc3 `err != nil` = T
    branch br:c71158777bce `err != nil` = T
  branch br:0746154f1c47 `err != nil` = T
  call gapi.unauthenticatedError(err=*errors.errorString#e35f8d) [returned-error:go:*status.Error]

### TestUpdateUserAPI/InvalidEmail  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned-error:go:*status.Error; gapi.Server.authorizeUser returned; gapi.hasPermission returned
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
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#60d1da) [returned] -> #0dd246
    call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
      branch br:5afefe007454 `x != nil` = T
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
      branch br:5e873717aade `x != nil && x.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    call pb.UpdateUserRequest.GetEmail() [returned] -> #95ee90
      branch br:e041dd12b17a `x != nil && x.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = T
  branch br:af0e24f4367b `violations != nil` = T
  call gapi.invalidArgumentError(violations=[]*errdetails.BadRequest_FieldViolation[1]#0dd246) [returned-error:go:*status.Error]
    branch br:ebc242daf335 `err != nil` = F

### TestUpdateUserAPI/NoAuthorization  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error; gapi.Server.authorizeUser returned-error:go:*errors.errorString
call gapi.Server.UpdateUser(ctx=context.backgroundCtx#2e2a50, req=*pb.UpdateUserRequest#134c96) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=context.backgroundCtx#2e2a50, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = T
  branch br:0746154f1c47 `err != nil` = T
  call gapi.unauthenticatedError(err=*errors.errorString#e35f8d) [returned-error:go:*status.Error]

### TestUpdateUserAPI/OK  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned; gapi.Server.authorizeUser returned; gapi.hasPermission returned
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
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
      branch br:5afefe007454 `x != nil` = T
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
      branch br:5e873717aade `x != nil && x.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
      branch br:e041dd12b17a `x != nil && x.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
    branch br:5e873717aade `x != nil && x.FullName != nil` = T
  call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
    branch br:e041dd12b17a `x != nil && x.Email != nil` = T
  branch br:815be3bfb43a `req.Password != nil` = F
  branch br:17f2bce25a0f `err != nil` = F
  call gapi.convertUser(user=db.User#c38c92) [returned]

### TestUpdateUserAPI/OtherDepositorCannotUpdateThisUserInfo  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned-error:go:*status.Error; gapi.Server.authorizeUser returned; gapi.hasPermission returned
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
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
      branch br:5afefe007454 `x != nil` = T
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
      branch br:5e873717aade `x != nil && x.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
      branch br:e041dd12b17a `x != nil && x.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = T

### TestUpdateUserAPI/UserNotFound  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.UpdateUser returned-error:go:*status.Error; gapi.Server.authorizeUser returned; gapi.hasPermission returned
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
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#134c96) [returned] -> #e96533
    call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
      branch br:5afefe007454 `x != nil` = T
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
      branch br:5e873717aade `x != nil && x.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
      branch br:e041dd12b17a `x != nil && x.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  call pb.UpdateUserRequest.GetUsername() [returned] -> #26b18a
    branch br:5afefe007454 `x != nil` = T
  call pb.UpdateUserRequest.GetFullName() [returned] -> #4eee28
    branch br:5e873717aade `x != nil && x.FullName != nil` = T
  call pb.UpdateUserRequest.GetEmail() [returned] -> #a7e905
    branch br:e041dd12b17a `x != nil && x.Email != nil` = T
  branch br:815be3bfb43a `req.Password != nil` = F
  branch br:17f2bce25a0f `err != nil` = T
  branch br:fb1ba40798cf `errors.Is(err, db.ErrRecordNotFound)` = T
```

## The change (git diff 6e2679863e4c691db46ec14761a3b3e303e05ce1..2e2094e209a2e9432b53a0d142f52bc8ccce82c2, the files shown below)

```diff
diff --git a/api/token.go b/api/token.go
index 924ffd4..7d7b615 100644
--- a/api/token.go
+++ b/api/token.go
@@ -46,38 +46,39 @@ func (server *Server) renewAccessToken(ctx *gin.Context) {
 		err := fmt.Errorf("blocked session")
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	if session.Username != refreshPayload.Username {
 		err := fmt.Errorf("incorrect session user")
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	if session.RefreshToken != req.RefreshToken {
 		err := fmt.Errorf("mismatched session token")
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	if time.Now().After(session.ExpiresAt) {
 		err := fmt.Errorf("expired session")
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		refreshPayload.Username,
+		refreshPayload.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	rsp := renewAccessTokenResponse{
 		AccessToken:          accessToken,
 		AccessTokenExpiresAt: accessPayload.ExpiredAt,
 	}
 	ctx.JSON(http.StatusOK, rsp)
 }
diff --git a/api/user.go b/api/user.go
index 65ce1a5..94de476 100644
--- a/api/user.go
+++ b/api/user.go
@@ -87,59 +87,61 @@ type loginUserResponse struct {
 func (server *Server) loginUser(ctx *gin.Context) {
 	var req loginUserRequest
 	if err := ctx.ShouldBindJSON(&req); err != nil {
 		ctx.JSON(http.StatusBadRequest, errorResponse(err))
 		return
 	}
 
 	user, err := server.store.GetUser(ctx, req.Username)
 	if err != nil {
 		if errors.Is(err, db.ErrRecordNotFound) {
 			ctx.JSON(http.StatusNotFound, errorResponse(err))
 			return
 		}
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	err = util.CheckPassword(req.Password, user.HashedPassword)
 	if err != nil {
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.RefreshTokenDuration,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
 		ID:           refreshPayload.ID,
 		Username:     user.Username,
 		RefreshToken: refreshToken,
 		UserAgent:    ctx.Request.UserAgent(),
 		ClientIp:     ctx.ClientIP(),
 		IsBlocked:    false,
 		ExpiresAt:    refreshPayload.ExpiredAt,
 	})
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	rsp := loginUserResponse{
 		SessionID:             session.ID,
 		AccessToken:           accessToken,
 		AccessTokenExpiresAt:  accessPayload.ExpiredAt,
diff --git a/gapi/authorization.go b/gapi/authorization.go
index e7e5583..892467d 100644
--- a/gapi/authorization.go
+++ b/gapi/authorization.go
@@ -1,46 +1,59 @@
 package gapi
 
 import (
 	"context"
 	"fmt"
 	"strings"
 
 	"github.com/techschool/simplebank/token"
 	"google.golang.org/grpc/metadata"
 )
 
 const (
 	authorizationHeader = "authorization"
 	authorizationBearer = "bearer"
 )
 
-func (server *Server) authorizeUser(ctx context.Context) (*token.Payload, error) {
+func (server *Server) authorizeUser(ctx context.Context, accessibleRoles []string) (*token.Payload, error) {
 	md, ok := metadata.FromIncomingContext(ctx)
 	if !ok {
 		return nil, fmt.Errorf("missing metadata")
 	}
 
 	values := md.Get(authorizationHeader)
 	if len(values) == 0 {
 		return nil, fmt.Errorf("missing authorization header")
 	}
 
 	authHeader := values[0]
 	fields := strings.Fields(authHeader)
 	if len(fields) < 2 {
 		return nil, fmt.Errorf("invalid authorization header format")
 	}
 
 	authType := strings.ToLower(fields[0])
 	if authType != authorizationBearer {
 		return nil, fmt.Errorf("unsupported authorization type: %s", authType)
 	}
 
 	accessToken := fields[1]
 	payload, err := server.tokenMaker.VerifyToken(accessToken)
 	if err != nil {
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
@@ -13,58 +13,60 @@ import (
 	"google.golang.org/grpc/status"
 	"google.golang.org/protobuf/types/known/timestamppb"
 )
 
 func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (*pb.LoginUserResponse, error) {
 	violations := validateLoginUserRequest(req)
 	if violations != nil {
 		return nil, invalidArgumentError(violations)
 	}
 
 	user, err := server.store.GetUser(ctx, req.GetUsername())
 	if err != nil {
 		if errors.Is(err, db.ErrRecordNotFound) {
 			return nil, status.Errorf(codes.NotFound, "user not found")
 		}
 		return nil, status.Errorf(codes.Internal, "failed to find user")
 	}
 
 	err = util.CheckPassword(req.Password, user.HashedPassword)
 	if err != nil {
 		return nil, status.Errorf(codes.NotFound, "incorrect password")
 	}
 
 	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.AccessTokenDuration,
 	)
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create access token")
 	}
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
+		user.Role,
 		server.config.RefreshTokenDuration,
 	)
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create refresh token")
 	}
 
 	mtdt := server.extractMetadata(ctx)
 	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
 		ID:           refreshPayload.ID,
 		Username:     user.Username,
 		RefreshToken: refreshToken,
 		UserAgent:    mtdt.UserAgent,
 		ClientIp:     mtdt.ClientIP,
 		IsBlocked:    false,
 		ExpiresAt:    refreshPayload.ExpiredAt,
 	})
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create session")
 	}
 
 	rsp := &pb.LoginUserResponse{
 		User:                  convertUser(user),
 		SessionId:             session.ID.String(),
 		AccessToken:           accessToken,
 		RefreshToken:          refreshToken,
diff --git a/gapi/rpc_update_user.go b/gapi/rpc_update_user.go
index 2b5ef8d..2a290cd 100644
--- a/gapi/rpc_update_user.go
+++ b/gapi/rpc_update_user.go
@@ -1,54 +1,54 @@
 package gapi
 
 import (
 	"context"
 	"errors"
 	"time"
 
 	"github.com/jackc/pgx/v5/pgtype"
 	db "github.com/techschool/simplebank/db/sqlc"
 	"github.com/techschool/simplebank/pb"
 	"github.com/techschool/simplebank/util"
 	"github.com/techschool/simplebank/val"
 	"google.golang.org/genproto/googleapis/rpc/errdetails"
 	"google.golang.org/grpc/codes"
 	"google.golang.org/grpc/status"
 )
 
 func (server *Server) UpdateUser(ctx context.Context, req *pb.UpdateUserRequest) (*pb.UpdateUserResponse, error) {
-	authPayload, err := server.authorizeUser(ctx)
+	authPayload, err := server.authorizeUser(ctx, []string{util.BankerRole, util.DepositorRole})
 	if err != nil {
 		return nil, unauthenticatedError(err)
 	}
 
 	violations := validateUpdateUserRequest(req)
 	if violations != nil {
 		return nil, invalidArgumentError(violations)
 	}
 
-	if authPayload.Username != req.GetUsername() {
+	if authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername() {
 		return nil, status.Errorf(codes.PermissionDenied, "cannot update other user's info")
 	}
 
 	arg := db.UpdateUserParams{
 		Username: req.GetUsername(),
 		FullName: pgtype.Text{
 			String: req.GetFullName(),
 			Valid:  req.FullName != nil,
 		},
 		Email: pgtype.Text{
 			String: req.GetEmail(),
 			Valid:  req.Email != nil,
 		},
 	}
 
 	if req.Password != nil {
 		hashedPassword, err := util.HashPassword(req.GetPassword())
 		if err != nil {
 			return nil, status.Errorf(codes.Internal, "failed to hash password: %s", err)
 		}
 
 		arg.HashedPassword = pgtype.Text{
 			String: hashedPassword,
 			Valid:  true,
 		}
diff --git a/token/jwt_maker.go b/token/jwt_maker.go
index 2df8f2a..02d7cdd 100644
--- a/token/jwt_maker.go
+++ b/token/jwt_maker.go
@@ -2,52 +2,52 @@ package token
 
 import (
 	"errors"
 	"fmt"
 	"time"
 
 	"github.com/dgrijalva/jwt-go"
 )
 
 const minSecretKeySize = 32
 
 // JWTMaker is a JSON Web Token maker
 type JWTMaker struct {
 	secretKey string
 }
 
 // NewJWTMaker creates a new JWTMaker
 func NewJWTMaker(secretKey string) (Maker, error) {
 	if len(secretKey) < minSecretKeySize {
 		return nil, fmt.Errorf("invalid key size: must be at least %d characters", minSecretKeySize)
 	}
 	return &JWTMaker{secretKey}, nil
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *JWTMaker) CreateToken(username string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, duration)
+func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration)
 	if err != nil {
 		return "", payload, err
 	}
 
 	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, payload)
 	token, err := jwtToken.SignedString([]byte(maker.secretKey))
 	return token, payload, err
 }
 
 // VerifyToken checks if the token is valid or not
 func (maker *JWTMaker) VerifyToken(token string) (*Payload, error) {
 	keyFunc := func(token *jwt.Token) (interface{}, error) {
 		_, ok := token.Method.(*jwt.SigningMethodHMAC)
 		if !ok {
 			return nil, ErrInvalidToken
 		}
 		return []byte(maker.secretKey), nil
 	}
 
 	jwtToken, err := jwt.ParseWithClaims(token, &Payload{}, keyFunc)
 	if err != nil {
 		verr, ok := err.(*jwt.ValidationError)
 		if ok && errors.Is(verr.Inner, ErrExpiredToken) {
 			return nil, ErrExpiredToken
 		}
diff --git a/token/maker.go b/token/maker.go
index 2228d05..9466e78 100644
--- a/token/maker.go
+++ b/token/maker.go
@@ -1,14 +1,14 @@
 package token
 
 import (
 	"time"
 )
 
 // Maker is an interface for managing tokens
 type Maker interface {
 	// CreateToken creates a new token for a specific username and duration
-	CreateToken(username string, duration time.Duration) (string, *Payload, error)
+	CreateToken(username string, role string, duration time.Duration) (string, *Payload, error)
 
 	// VerifyToken checks if the token is valid or not
 	VerifyToken(token string) (*Payload, error)
 }
diff --git a/token/paseto_maker.go b/token/paseto_maker.go
index 0f63d5e..d855837 100644
--- a/token/paseto_maker.go
+++ b/token/paseto_maker.go
@@ -7,51 +7,51 @@ import (
 	"github.com/aead/chacha20poly1305"
 	"github.com/o1egl/paseto"
 )
 
 // PasetoMaker is a PASETO token maker
 type PasetoMaker struct {
 	paseto       *paseto.V2
 	symmetricKey []byte
 }
 
 // NewPasetoMaker creates a new PasetoMaker
 func NewPasetoMaker(symmetricKey string) (Maker, error) {
 	if len(symmetricKey) != chacha20poly1305.KeySize {
 		return nil, fmt.Errorf("invalid key size: must be exactly %d characters", chacha20poly1305.KeySize)
 	}
 
 	maker := &PasetoMaker{
 		paseto:       paseto.NewV2(),
 		symmetricKey: []byte(symmetricKey),
 	}
 
 	return maker, nil
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *PasetoMaker) CreateToken(username string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, duration)
+func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration)
 	if err != nil {
 		return "", payload, err
 	}
 
 	token, err := maker.paseto.Encrypt(maker.symmetricKey, payload, nil)
 	return token, payload, err
 }
 
 // VerifyToken checks if the token is valid or not
 func (maker *PasetoMaker) VerifyToken(token string) (*Payload, error) {
 	payload := &Payload{}
 
 	err := maker.paseto.Decrypt(token, maker.symmetricKey, payload, nil)
 	if err != nil {
 		return nil, ErrInvalidToken
 	}
 
 	err = payload.Valid()
 	if err != nil {
 		return nil, err
 	}
 
 	return payload, nil
 }
diff --git a/token/payload.go b/token/payload.go
index 9645a55..dccae11 100644
--- a/token/payload.go
+++ b/token/payload.go
@@ -1,46 +1,48 @@
 package token
 
 import (
 	"errors"
 	"time"
 
 	"github.com/google/uuid"
 )
 
 // Different types of error returned by the VerifyToken function
 var (
 	ErrInvalidToken = errors.New("token is invalid")
 	ErrExpiredToken = errors.New("token has expired")
 )
 
 // Payload contains the payload data of the token
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
 	}
 
 	payload := &Payload{
 		ID:        tokenID,
 		Username:  username,
+		Role:      role,
 		IssuedAt:  time.Now(),
 		ExpiredAt: time.Now().Add(duration),
 	}
 	return payload, nil
 }
 
 // Valid checks if the token payload is valid or not
 func (payload *Payload) Valid() error {
 	if time.Now().After(payload.ExpiredAt) {
 		return ErrExpiredToken
 	}
 	return nil
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

## Source: gapi/authorization.go

```
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

## Source: gapi/converter.go

```
   1  package gapi
   2  
   3  import (
   4  	db "github.com/techschool/simplebank/db/sqlc"
   5  	"github.com/techschool/simplebank/pb"
   6  	"google.golang.org/protobuf/types/known/timestamppb"
   7  )
   8  
   9  func convertUser(user db.User) *pb.User {
  10  	return &pb.User{
  11  		Username:          user.Username,
  12  		FullName:          user.FullName,
  13  		Email:             user.Email,
  14  		PasswordChangedAt: timestamppb.New(user.PasswordChangedAt),
  15  		CreatedAt:         timestamppb.New(user.CreatedAt),
  16  	}
  17  }
```

## Source: gapi/error.go

```
   1  package gapi
   2  
   3  import (
   4  	"google.golang.org/genproto/googleapis/rpc/errdetails"
   5  	"google.golang.org/grpc/codes"
   6  	"google.golang.org/grpc/status"
   7  )
   8  
   9  func fieldViolation(field string, err error) *errdetails.BadRequest_FieldViolation {
  10  	return &errdetails.BadRequest_FieldViolation{
  11  		Field:       field,
  12  		Description: err.Error(),
  13  	}
  14  }
  15  
  16  func invalidArgumentError(violations []*errdetails.BadRequest_FieldViolation) error {
  17  	badRequest := &errdetails.BadRequest{FieldViolations: violations}
  18  	statusInvalid := status.New(codes.InvalidArgument, "invalid parameters")
  19  
  20  	statusDetails, err := statusInvalid.WithDetails(badRequest)
  21  	if err != nil {
  22  		return statusInvalid.Err()
  23  	}
  24  
  25  	return statusDetails.Err()
  26  }
  27  
  28  func unauthenticatedError(err error) error {
  29  	return status.Errorf(codes.Unauthenticated, "unauthorized: %s", err)
  30  }
```

## Source: gapi/rpc_update_user.go

```
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

## Source: pb/rpc_update_user.pb.go

```
   1  // Code generated by protoc-gen-go. DO NOT EDIT.
   2  // versions:
   3  // 	protoc-gen-go v1.28.1
   4  // 	protoc        v4.24.3
   5  // source: rpc_update_user.proto
   6  
   7  package pb
   8  
   9  import (
  10  	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
  11  	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
  12  	reflect "reflect"
  13  	sync "sync"
  14  )
  15  
  16  const (
  17  	// Verify that this generated code is sufficiently up-to-date.
  18  	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
  19  	// Verify that runtime/protoimpl is sufficiently up-to-date.
  20  	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
  21  )
  22  
  23  type UpdateUserRequest struct {
  24  	state         protoimpl.MessageState
  25  	sizeCache     protoimpl.SizeCache
  26  	unknownFields protoimpl.UnknownFields
  27  
  28  	Username string  `protobuf:"bytes,1,opt,name=username,proto3" json:"username,omitempty"`
  29  	FullName *string `protobuf:"bytes,2,opt,name=full_name,json=fullName,proto3,oneof" json:"full_name,omitempty"`
  30  	Email    *string `protobuf:"bytes,3,opt,name=email,proto3,oneof" json:"email,omitempty"`
  31  	Password *string `protobuf:"bytes,4,opt,name=password,proto3,oneof" json:"password,omitempty"`
  32  }
  33  
  34  func (x *UpdateUserRequest) Reset() {
  35  	*x = UpdateUserRequest{}
  36  	if protoimpl.UnsafeEnabled {
  37  		mi := &file_rpc_update_user_proto_msgTypes[0]
  38  		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
  39  		ms.StoreMessageInfo(mi)
  40  	}
  41  }
  42  
  43  func (x *UpdateUserRequest) String() string {
  44  	return protoimpl.X.MessageStringOf(x)
  45  }
  46  
  47  func (*UpdateUserRequest) ProtoMessage() {}
  48  
  49  func (x *UpdateUserRequest) ProtoReflect() protoreflect.Message {
  50  	mi := &file_rpc_update_user_proto_msgTypes[0]
  51  	if protoimpl.UnsafeEnabled && x != nil {
  52  		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
  53  		if ms.LoadMessageInfo() == nil {
  54  			ms.StoreMessageInfo(mi)
  55  		}
  56  		return ms
  57  	}
  58  	return mi.MessageOf(x)
  59  }
  60  
  61  // Deprecated: Use UpdateUserRequest.ProtoReflect.Descriptor instead.
  62  func (*UpdateUserRequest) Descriptor() ([]byte, []int) {
  63  	return file_rpc_update_user_proto_rawDescGZIP(), []int{0}
  64  }
  65  
  66  func (x *UpdateUserRequest) GetUsername() string {
  67  	if x != nil {
  68  		return x.Username
  69  	}
  70  	return ""
  71  }
  72  
  73  func (x *UpdateUserRequest) GetFullName() string {
  74  	if x != nil && x.FullName != nil {
  75  		return *x.FullName
  76  	}
  77  	return ""
  78  }
  79  
  80  func (x *UpdateUserRequest) GetEmail() string {
  81  	if x != nil && x.Email != nil {
  82  		return *x.Email
  83  	}
  84  	return ""
  85  }
  86  
  87  func (x *UpdateUserRequest) GetPassword() string {
  88  	if x != nil && x.Password != nil {
  89  		return *x.Password
  90  	}
  91  	return ""
  92  }
  93  
  94  type UpdateUserResponse struct {
  95  	state         protoimpl.MessageState
  96  	sizeCache     protoimpl.SizeCache
  97  	unknownFields protoimpl.UnknownFields
  98  
  99  	User *User `protobuf:"bytes,1,opt,name=user,proto3" json:"user,omitempty"`
 100  }
 101  
 102  func (x *UpdateUserResponse) Reset() {
 103  	*x = UpdateUserResponse{}
 104  	if protoimpl.UnsafeEnabled {
 105  		mi := &file_rpc_update_user_proto_msgTypes[1]
 106  		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
 107  		ms.StoreMessageInfo(mi)
 108  	}
 109  }
 110  
 111  func (x *UpdateUserResponse) String() string {
 112  	return protoimpl.X.MessageStringOf(x)
 113  }
 114  
 115  func (*UpdateUserResponse) ProtoMessage() {}
 116  
 117  func (x *UpdateUserResponse) ProtoReflect() protoreflect.Message {
 118  	mi := &file_rpc_update_user_proto_msgTypes[1]
 119  	if protoimpl.UnsafeEnabled && x != nil {
 120  		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
 121  		if ms.LoadMessageInfo() == nil {
 122  			ms.StoreMessageInfo(mi)
 123  		}
 124  		return ms
 125  	}
 126  	return mi.MessageOf(x)
 127  }
 128  
 129  // Deprecated: Use UpdateUserResponse.ProtoReflect.Descriptor instead.
 130  func (*UpdateUserResponse) Descriptor() ([]byte, []int) {
 131  	return file_rpc_update_user_proto_rawDescGZIP(), []int{1}
 132  }
 133  
 134  func (x *UpdateUserResponse) GetUser() *User {
 135  	if x != nil {
 136  		return x.User
 137  	}
 138  	return nil
 139  }
 140  
 141  var File_rpc_update_user_proto protoreflect.FileDescriptor
 142  
 143  var file_rpc_update_user_proto_rawDesc = []byte{
 144  	0x0a, 0x15, 0x72, 0x70, 0x63, 0x5f, 0x75, 0x70, 0x64, 0x61, 0x74, 0x65, 0x5f, 0x75, 0x73, 0x65,
 145  	0x72, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x12, 0x02, 0x70, 0x62, 0x1a, 0x0a, 0x75, 0x73, 0x65,
 146  	0x72, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x22, 0xb2, 0x01, 0x0a, 0x11, 0x55, 0x70, 0x64, 0x61,
 147  	0x74, 0x65, 0x55, 0x73, 0x65, 0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x1a, 0x0a,
 148  	0x08, 0x75, 0x73, 0x65, 0x72, 0x6e, 0x61, 0x6d, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09, 0x52,
 149  	0x08, 0x75, 0x73, 0x65, 0x72, 0x6e, 0x61, 0x6d, 0x65, 0x12, 0x20, 0x0a, 0x09, 0x66, 0x75, 0x6c,
 150  	0x6c, 0x5f, 0x6e, 0x61, 0x6d, 0x65, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x48, 0x00, 0x52, 0x08,
 151  	0x66, 0x75, 0x6c, 0x6c, 0x4e, 0x61, 0x6d, 0x65, 0x88, 0x01, 0x01, 0x12, 0x19, 0x0a, 0x05, 0x65,
 152  	0x6d, 0x61, 0x69, 0x6c, 0x18, 0x03, 0x20, 0x01, 0x28, 0x09, 0x48, 0x01, 0x52, 0x05, 0x65, 0x6d,
 153  	0x61, 0x69, 0x6c, 0x88, 0x01, 0x01, 0x12, 0x1f, 0x0a, 0x08, 0x70, 0x61, 0x73, 0x73, 0x77, 0x6f,
 154  	0x72, 0x64, 0x18, 0x04, 0x20, 0x01, 0x28, 0x09, 0x48, 0x02, 0x52, 0x08, 0x70, 0x61, 0x73, 0x73,
 155  	0x77, 0x6f, 0x72, 0x64, 0x88, 0x01, 0x01, 0x42, 0x0c, 0x0a, 0x0a, 0x5f, 0x66, 0x75, 0x6c, 0x6c,
 156  	0x5f, 0x6e, 0x61, 0x6d, 0x65, 0x42, 0x08, 0x0a, 0x06, 0x5f, 0x65, 0x6d, 0x61, 0x69, 0x6c, 0x42,
 157  	0x0b, 0x0a, 0x09, 0x5f, 0x70, 0x61, 0x73, 0x73, 0x77, 0x6f, 0x72, 0x64, 0x22, 0x32, 0x0a, 0x12,
 158  	0x55, 0x70, 0x64, 0x61, 0x74, 0x65, 0x55, 0x73, 0x65, 0x72, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e,
 159  	0x73, 0x65, 0x12, 0x1c, 0x0a, 0x04, 0x75, 0x73, 0x65, 0x72, 0x18, 0x01, 0x20, 0x01, 0x28, 0x0b,
 160  	0x32, 0x08, 0x2e, 0x70, 0x62, 0x2e, 0x55, 0x73, 0x65, 0x72, 0x52, 0x04, 0x75, 0x73, 0x65, 0x72,
 161  	0x42, 0x25, 0x5a, 0x23, 0x67, 0x69, 0x74, 0x68, 0x75, 0x62, 0x2e, 0x63, 0x6f, 0x6d, 0x2f, 0x74,
 162  	0x65, 0x63, 0x68, 0x73, 0x63, 0x68, 0x6f, 0x6f, 0x6c, 0x2f, 0x73, 0x69, 0x6d, 0x70, 0x6c, 0x65,
 163  	0x62, 0x61, 0x6e, 0x6b, 0x2f, 0x70, 0x62, 0x62, 0x06, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x33,
 164  }
 165  
 166  var (
 167  	file_rpc_update_user_proto_rawDescOnce sync.Once
 168  	file_rpc_update_user_proto_rawDescData = file_rpc_update_user_proto_rawDesc
 169  )
 170  
 171  func file_rpc_update_user_proto_rawDescGZIP() []byte {
 172  	file_rpc_update_user_proto_rawDescOnce.Do(func() {
 173  		file_rpc_update_user_proto_rawDescData = protoimpl.X.CompressGZIP(file_rpc_update_user_proto_rawDescData)
 174  	})
 175  	return file_rpc_update_user_proto_rawDescData
 176  }
 177  
 178  var file_rpc_update_user_proto_msgTypes = make([]protoimpl.MessageInfo, 2)
 179  var file_rpc_update_user_proto_goTypes = []interface{}{
 180  	(*UpdateUserRequest)(nil),  // 0: pb.UpdateUserRequest
 181  	(*UpdateUserResponse)(nil), // 1: pb.UpdateUserResponse
 182  	(*User)(nil),               // 2: pb.User
 183  }
 184  var file_rpc_update_user_proto_depIdxs = []int32{
 185  	2, // 0: pb.UpdateUserResponse.user:type_name -> pb.User
 186  	1, // [1:1] is the sub-list for method output_type
 187  	1, // [1:1] is the sub-list for method input_type
 188  	1, // [1:1] is the sub-list for extension type_name
 189  	1, // [1:1] is the sub-list for extension extendee
 190  	0, // [0:1] is the sub-list for field type_name
 191  }
 192  
 193  func init() { file_rpc_update_user_proto_init() }
 194  func file_rpc_update_user_proto_init() {
 195  	if File_rpc_update_user_proto != nil {
 196  		return
 197  	}
 198  	file_user_proto_init()
 199  	if !protoimpl.UnsafeEnabled {
 200  		file_rpc_update_user_proto_msgTypes[0].Exporter = func(v interface{}, i int) interface{} {
 201  			switch v := v.(*UpdateUserRequest); i {
 202  			case 0:
 203  				return &v.state
 204  			case 1:
 205  				return &v.sizeCache
 206  			case 2:
 207  				return &v.unknownFields
 208  			default:
 209  				return nil
 210  			}
 211  		}
 212  		file_rpc_update_user_proto_msgTypes[1].Exporter = func(v interface{}, i int) interface{} {
 213  			switch v := v.(*UpdateUserResponse); i {
 214  			case 0:
 215  				return &v.state
 216  			case 1:
 217  				return &v.sizeCache
 218  			case 2:
 219  				return &v.unknownFields
 220  			default:
 221  				return nil
 222  			}
 223  		}
 224  	}
 225  	file_rpc_update_user_proto_msgTypes[0].OneofWrappers = []interface{}{}
 226  	type x struct{}
 227  	out := protoimpl.TypeBuilder{
 228  		File: protoimpl.DescBuilder{
 229  			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
 230  			RawDescriptor: file_rpc_update_user_proto_rawDesc,
 231  			NumEnums:      0,
 232  			NumMessages:   2,
 233  			NumExtensions: 0,
 234  			NumServices:   0,
 235  		},
 236  		GoTypes:           file_rpc_update_user_proto_goTypes,
 237  		DependencyIndexes: file_rpc_update_user_proto_depIdxs,
 238  		MessageInfos:      file_rpc_update_user_proto_msgTypes,
 239  	}.Build()
 240  	File_rpc_update_user_proto = out.File
 241  	file_rpc_update_user_proto_rawDesc = nil
 242  	file_rpc_update_user_proto_goTypes = nil
 243  	file_rpc_update_user_proto_depIdxs = nil
 244  }
```

## Source: token/paseto_maker.go

```
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

## Source: token/payload.go

```
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

## Source: util/role.go

```
   1  package util
   2  
   3  const (
   4  	DepositorRole = "depositor"
   5  	BankerRole    = "banker"
   6  )
```

## Source: token/maker.go

```
   1  package token
   2  
   3  import (
   4  	"time"
   5  )
   6  
   7  // Maker is an interface for managing tokens
   8  type Maker interface {
   9  	// CreateToken creates a new token for a specific username and duration
  10  	CreateToken(username string, role string, duration time.Duration) (string, *Payload, error)
  11  
  12  	// VerifyToken checks if the token is valid or not
  13  	VerifyToken(token string) (*Payload, error)
  14  }
```

## Source: token/jwt_maker.go

```
   1  package token
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"time"
   7  
   8  	"github.com/dgrijalva/jwt-go"
   9  )
  10  
  11  const minSecretKeySize = 32
  12  
  13  // JWTMaker is a JSON Web Token maker
  14  type JWTMaker struct {
  15  	secretKey string
  16  }
  17  
  18  // NewJWTMaker creates a new JWTMaker
  19  func NewJWTMaker(secretKey string) (Maker, error) {
  20  	if len(secretKey) < minSecretKeySize {
  21  		return nil, fmt.Errorf("invalid key size: must be at least %d characters", minSecretKeySize)
  22  	}
  23  	return &JWTMaker{secretKey}, nil
  24  }
  25  
  26  // CreateToken creates a new token for a specific username and duration
  27  func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
  28  	payload, err := NewPayload(username, role, duration)
  29  	if err != nil {
  30  		return "", payload, err
  31  	}
  32  
  33  	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, payload)
  34  	token, err := jwtToken.SignedString([]byte(maker.secretKey))
  35  	return token, payload, err
  36  }
  37  
  38  // VerifyToken checks if the token is valid or not
  39  func (maker *JWTMaker) VerifyToken(token string) (*Payload, error) {
  40  	keyFunc := func(token *jwt.Token) (interface{}, error) {
  41  		_, ok := token.Method.(*jwt.SigningMethodHMAC)
  42  		if !ok {
  43  			return nil, ErrInvalidToken
  44  		}
  45  		return []byte(maker.secretKey), nil
  46  	}
  47  
  48  	jwtToken, err := jwt.ParseWithClaims(token, &Payload{}, keyFunc)
  49  	if err != nil {
  50  		verr, ok := err.(*jwt.ValidationError)
  51  		if ok && errors.Is(verr.Inner, ErrExpiredToken) {
  52  			return nil, ErrExpiredToken
  53  		}
  54  		return nil, ErrInvalidToken
  55  	}
  56  
  57  	payload, ok := jwtToken.Claims.(*Payload)
  58  	if !ok {
  59  		return nil, ErrInvalidToken
  60  	}
  61  
  62  	return payload, nil
  63  }
```

## Source: api/token.go

```
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"net/http"
   7  	"time"
   8  
   9  	"github.com/gin-gonic/gin"
  10  	db "github.com/techschool/simplebank/db/sqlc"
  11  )
  12  
  13  type renewAccessTokenRequest struct {
  14  	RefreshToken string `json:"refresh_token" binding:"required"`
  15  }
  16  
  17  type renewAccessTokenResponse struct {
  18  	AccessToken          string    `json:"access_token"`
  19  	AccessTokenExpiresAt time.Time `json:"access_token_expires_at"`
  20  }
  21  
  22  func (server *Server) renewAccessToken(ctx *gin.Context) {
  23  	var req renewAccessTokenRequest
  24  	if err := ctx.ShouldBindJSON(&req); err != nil {
  25  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  26  		return
  27  	}
  28  
  29  	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken)
  30  	if err != nil {
  31  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  32  		return
  33  	}
  34  
  35  	session, err := server.store.GetSession(ctx, refreshPayload.ID)
  36  	if err != nil {
  37  		if errors.Is(err, db.ErrRecordNotFound) {
  38  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  39  			return
  40  		}
  41  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  42  		return
  43  	}
  44  
  45  	if session.IsBlocked {
  46  		err := fmt.Errorf("blocked session")
  47  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  48  		return
  49  	}
  50  
  51  	if session.Username != refreshPayload.Username {
  52  		err := fmt.Errorf("incorrect session user")
  53  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  54  		return
  55  	}
  56  
  57  	if session.RefreshToken != req.RefreshToken {
  58  		err := fmt.Errorf("mismatched session token")
  59  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  60  		return
  61  	}
  62  
  63  	if time.Now().After(session.ExpiresAt) {
  64  		err := fmt.Errorf("expired session")
  65  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  66  		return
  67  	}
  68  
  69  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
  70  		refreshPayload.Username,
  71  		refreshPayload.Role,
  72  		server.config.AccessTokenDuration,
  73  	)
  74  	if err != nil {
  75  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  76  		return
  77  	}
  78  
  79  	rsp := renewAccessTokenResponse{
  80  		AccessToken:          accessToken,
  81  		AccessTokenExpiresAt: accessPayload.ExpiredAt,
  82  	}
  83  	ctx.JSON(http.StatusOK, rsp)
  84  }
```

## Source: gapi/rpc_login_user.go

```
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"errors"
   6  
   7  	db "github.com/techschool/simplebank/db/sqlc"
   8  	"github.com/techschool/simplebank/pb"
   9  	"github.com/techschool/simplebank/util"
  10  	"github.com/techschool/simplebank/val"
  11  	"google.golang.org/genproto/googleapis/rpc/errdetails"
  12  	"google.golang.org/grpc/codes"
  13  	"google.golang.org/grpc/status"
  14  	"google.golang.org/protobuf/types/known/timestamppb"
  15  )
  16  
  17  func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (*pb.LoginUserResponse, error) {
  18  	violations := validateLoginUserRequest(req)
  19  	if violations != nil {
  20  		return nil, invalidArgumentError(violations)
  21  	}
  22  
  23  	user, err := server.store.GetUser(ctx, req.GetUsername())
  24  	if err != nil {
  25  		if errors.Is(err, db.ErrRecordNotFound) {
  26  			return nil, status.Errorf(codes.NotFound, "user not found")
  27  		}
  28  		return nil, status.Errorf(codes.Internal, "failed to find user")
  29  	}
  30  
  31  	err = util.CheckPassword(req.Password, user.HashedPassword)
  32  	if err != nil {
  33  		return nil, status.Errorf(codes.NotFound, "incorrect password")
  34  	}
  35  
  36  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
  37  		user.Username,
  38  		user.Role,
  39  		server.config.AccessTokenDuration,
  40  	)
  41  	if err != nil {
  42  		return nil, status.Errorf(codes.Internal, "failed to create access token")
  43  	}
  44  
  45  	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
  46  		user.Username,
  47  		user.Role,
  48  		server.config.RefreshTokenDuration,
  49  	)
  50  	if err != nil {
  51  		return nil, status.Errorf(codes.Internal, "failed to create refresh token")
  52  	}
  53  
  54  	mtdt := server.extractMetadata(ctx)
  55  	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
  56  		ID:           refreshPayload.ID,
  57  		Username:     user.Username,
  58  		RefreshToken: refreshToken,
  59  		UserAgent:    mtdt.UserAgent,
  60  		ClientIp:     mtdt.ClientIP,
  61  		IsBlocked:    false,
  62  		ExpiresAt:    refreshPayload.ExpiredAt,
  63  	})
  64  	if err != nil {
  65  		return nil, status.Errorf(codes.Internal, "failed to create session")
  66  	}
  67  
  68  	rsp := &pb.LoginUserResponse{
  69  		User:                  convertUser(user),
  70  		SessionId:             session.ID.String(),
  71  		AccessToken:           accessToken,
  72  		RefreshToken:          refreshToken,
  73  		AccessTokenExpiresAt:  timestamppb.New(accessPayload.ExpiredAt),
  74  		RefreshTokenExpiresAt: timestamppb.New(refreshPayload.ExpiredAt),
  75  	}
  76  	return rsp, nil
  77  }
  78  
  79  func validateLoginUserRequest(req *pb.LoginUserRequest) (violations []*errdetails.BadRequest_FieldViolation) {
  80  	if err := val.ValidateUsername(req.GetUsername()); err != nil {
  81  		violations = append(violations, fieldViolation("username", err))
  82  	}
  83  
  84  	if err := val.ValidatePassword(req.GetPassword()); err != nil {
  85  		violations = append(violations, fieldViolation("password", err))
  86  	}
  87  
  88  	return violations
  89  }
```

## Source: api/user.go

```
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"net/http"
   6  	"time"
   7  
   8  	"github.com/gin-gonic/gin"
   9  	"github.com/google/uuid"
  10  	db "github.com/techschool/simplebank/db/sqlc"
  11  	"github.com/techschool/simplebank/util"
  12  )
  13  
  14  type createUserRequest struct {
  15  	Username string `json:"username" binding:"required,alphanum"`
  16  	Password string `json:"password" binding:"required,min=6"`
  17  	FullName string `json:"full_name" binding:"required"`
  18  	Email    string `json:"email" binding:"required,email"`
  19  }
  20  
  21  type userResponse struct {
  22  	Username          string    `json:"username"`
  23  	FullName          string    `json:"full_name"`
  24  	Email             string    `json:"email"`
  25  	PasswordChangedAt time.Time `json:"password_changed_at"`
  26  	CreatedAt         time.Time `json:"created_at"`
  27  }
  28  
  29  func newUserResponse(user db.User) userResponse {
  30  	return userResponse{
  31  		Username:          user.Username,
  32  		FullName:          user.FullName,
  33  		Email:             user.Email,
  34  		PasswordChangedAt: user.PasswordChangedAt,
  35  		CreatedAt:         user.CreatedAt,
  36  	}
  37  }
  38  
  39  func (server *Server) createUser(ctx *gin.Context) {
  40  	var req createUserRequest
  41  	if err := ctx.ShouldBindJSON(&req); err != nil {
  42  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  43  		return
  44  	}
  45  
  46  	hashedPassword, err := util.HashPassword(req.Password)
  47  	if err != nil {
  48  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  49  		return
  50  	}
  51  
  52  	arg := db.CreateUserParams{
  53  		Username:       req.Username,
  54  		HashedPassword: hashedPassword,
  55  		FullName:       req.FullName,
  56  		Email:          req.Email,
  57  	}
  58  
  59  	user, err := server.store.CreateUser(ctx, arg)
  60  	if err != nil {
  61  		if db.ErrorCode(err) == db.UniqueViolation {
  62  			ctx.JSON(http.StatusForbidden, errorResponse(err))
  63  			return
  64  		}
  65  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  66  		return
  67  	}
  68  
  69  	rsp := newUserResponse(user)
  70  	ctx.JSON(http.StatusOK, rsp)
  71  }
  72  
  73  type loginUserRequest struct {
  74  	Username string `json:"username" binding:"required,alphanum"`
  75  	Password string `json:"password" binding:"required,min=6"`
  76  }
  77  
  78  type loginUserResponse struct {
  79  	SessionID             uuid.UUID    `json:"session_id"`
  80  	AccessToken           string       `json:"access_token"`
  81  	AccessTokenExpiresAt  time.Time    `json:"access_token_expires_at"`
  82  	RefreshToken          string       `json:"refresh_token"`
  83  	RefreshTokenExpiresAt time.Time    `json:"refresh_token_expires_at"`
  84  	User                  userResponse `json:"user"`
  85  }
  86  
  87  func (server *Server) loginUser(ctx *gin.Context) {
  88  	var req loginUserRequest
  89  	if err := ctx.ShouldBindJSON(&req); err != nil {
  90  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  91  		return
  92  	}
  93  
  94  	user, err := server.store.GetUser(ctx, req.Username)
  95  	if err != nil {
  96  		if errors.Is(err, db.ErrRecordNotFound) {
  97  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  98  			return
  99  		}
 100  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 101  		return
 102  	}
 103  
 104  	err = util.CheckPassword(req.Password, user.HashedPassword)
 105  	if err != nil {
 106  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 107  		return
 108  	}
 109  
 110  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 111  		user.Username,
 112  		user.Role,
 113  		server.config.AccessTokenDuration,
 114  	)
 115  	if err != nil {
 116  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 117  		return
 118  	}
 119  
 120  	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 121  		user.Username,
 122  		user.Role,
 123  		server.config.RefreshTokenDuration,
 124  	)
 125  	if err != nil {
 126  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 127  		return
 128  	}
 129  
 130  	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
 131  		ID:           refreshPayload.ID,
 132  		Username:     user.Username,
 133  		RefreshToken: refreshToken,
 134  		UserAgent:    ctx.Request.UserAgent(),
 135  		ClientIp:     ctx.ClientIP(),
 136  		IsBlocked:    false,
 137  		ExpiresAt:    refreshPayload.ExpiredAt,
 138  	})
 139  	if err != nil {
 140  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 141  		return
 142  	}
 143  
 144  	rsp := loginUserResponse{
 145  		SessionID:             session.ID,
 146  		AccessToken:           accessToken,
 147  		AccessTokenExpiresAt:  accessPayload.ExpiredAt,
 148  		RefreshToken:          refreshToken,
 149  		RefreshTokenExpiresAt: refreshPayload.ExpiredAt,
 150  		User:                  newUserResponse(user),
 151  	}
 152  	ctx.JSON(http.StatusOK, rsp)
 153  }
```

## Source: gapi/rpc_update_user_test.go

```
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
