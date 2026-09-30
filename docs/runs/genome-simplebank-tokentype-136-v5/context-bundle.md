# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is simplebank #136 (upstream techschool/simplebank#136; fork sydes-examples/simplebank#4) (base 7c6f92f2 → head 97f000fe):
"add token type to token payload". A `TokenType` (`TokenTypeAccessToken = 1`, `TokenTypeRefreshToken = 2`) is passed to token creation and stored in the payload. Verification (`VerifyToken`, both the PASETO and the JWT maker) now takes the expected type, and `Payload.Valid` rejects a payload whose type differs with `ErrInvalidToken`. The gRPC `authorizeUser` and the HTTP `authMiddleware` expect access tokens; the HTTP `renewAccessToken` expects a refresh token; login creates one token of each type.

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

- br:eb7b1a216152 go:api.Server.loginUser line 90: `err != nil`   (not evaluated in the shown tests)
- br:84d886a24efe go:api.Server.loginUser line 96: `err != nil`   (not evaluated in the shown tests)
- br:e540ee8e596a go:api.Server.loginUser line 97: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:8ac57f80bf1d go:api.Server.loginUser line 106: `err != nil`   (not evaluated in the shown tests)
- br:b2bb97f7167b go:api.Server.loginUser line 117: `err != nil`   (not evaluated in the shown tests)
- br:81d23a5f3d1d go:api.Server.loginUser line 128: `err != nil`   (not evaluated in the shown tests)
- br:7fe5569cfdac go:api.Server.loginUser line 142: `err != nil`   (not evaluated in the shown tests)
- br:51914597d4b2 go:api.Server.renewAccessToken line 25: `err != nil`   (not evaluated in the shown tests)
- br:b98712eb46d4 go:api.Server.renewAccessToken line 31: `err != nil`   (not evaluated in the shown tests)
- br:d2add7aaa3bb go:api.Server.renewAccessToken line 37: `err != nil`   (not evaluated in the shown tests)
- br:c91282863028 go:api.Server.renewAccessToken line 38: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:4c153bb03d9c go:api.Server.renewAccessToken line 46: `session.IsBlocked`   (not evaluated in the shown tests)
- br:58d817da41f5 go:api.Server.renewAccessToken line 52: `session.Username != refreshPayload.Username`   (not evaluated in the shown tests)
- br:48d3578e9a44 go:api.Server.renewAccessToken line 58: `session.RefreshToken != req.RefreshToken`   (not evaluated in the shown tests)
- br:7b9ae91490eb go:api.Server.renewAccessToken line 64: `time.Now().After(session.ExpiresAt)`   (not evaluated in the shown tests)
- br:65b3034c3f05 go:api.Server.renewAccessToken line 76: `err != nil`   (not evaluated in the shown tests)
- br:bb32884fc4f0 go:gapi.Server.CreateUser line 20: `violations != nil`   (not evaluated in the shown tests)
- br:be27f218e30f go:gapi.Server.CreateUser line 25: `err != nil`   (not evaluated in the shown tests)
- br:086cd7460869 go:gapi.Server.CreateUser line 51: `err != nil`   (not evaluated in the shown tests)
- br:f9551788eb8d go:gapi.Server.CreateUser line 52: `db.ErrorCode(err) == db.UniqueViolation`   (not evaluated in the shown tests)
- br:76bc8d02ae40 go:gapi.Server.LoginUser line 20: `violations != nil`   (not evaluated in the shown tests)
- br:bbafcfbd5eed go:gapi.Server.LoginUser line 25: `err != nil`   (not evaluated in the shown tests)
- br:5524c0c4b7f1 go:gapi.Server.LoginUser line 26: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated in the shown tests)
- br:7b2947a85e0c go:gapi.Server.LoginUser line 33: `err != nil`   (not evaluated in the shown tests)
- br:85b863c14186 go:gapi.Server.LoginUser line 43: `err != nil`   (not evaluated in the shown tests)
- br:791afc927393 go:gapi.Server.LoginUser line 53: `err != nil`   (not evaluated in the shown tests)
- br:65d9ca0b3d0c go:gapi.Server.LoginUser line 67: `err != nil`   (not evaluated in the shown tests)
- br:e3505bc4c4b9 go:gapi.Server.authorizeUser line 19: `!ok`
- br:a572eeb6a4c8 go:gapi.Server.authorizeUser line 24: `len(values) == 0`
- br:4393757b65d7 go:gapi.Server.authorizeUser line 30: `len(fields) < 2`
- br:2e2f712d6301 go:gapi.Server.authorizeUser line 35: `authType != authorizationBearer`
- br:c71158777bce go:gapi.Server.authorizeUser line 41: `err != nil`
- br:c1bc39962889 go:gapi.Server.authorizeUser line 45: `!hasPermission(payload.Role, accessibleRoles)`
- br:d9f1e0c214f9 go:token.JWTMaker.CreateToken line 29: `err != nil`
- br:b95a526c7153 go:token.JWTMaker.VerifyToken line 49: `err != nil`
- br:184d2ca72d5b go:token.JWTMaker.VerifyToken line 50: `errors.Is(err, jwt.ErrTokenExpired)`
- br:46e44adad2e4 go:token.JWTMaker.VerifyToken line 57: `!ok`
- br:8a21855c007e go:token.JWTMaker.VerifyToken line 62: `err != nil`
- br:ecd8b89da8b7 go:token.NewPayload line 37: `err != nil`
- br:0713394c9923 go:token.PasetoMaker.CreateToken line 34: `err != nil`
- br:0607e4d952f6 go:token.PasetoMaker.VerifyToken line 47: `err != nil`
- br:c7d403dfabc3 go:token.PasetoMaker.VerifyToken line 52: `err != nil`
- br:8d10f2f9b136 go:token.Payload.Valid line 54: `payload.Type != tokenType`
- br:bdb0acf90853 go:token.Payload.Valid line 57: `time.Now().After(payload.ExpiredAt)`

Runtime-only required sites (observed; no static facts, e.g. in closures): br:052de203d9d4 in go:api.authMiddleware.<anon>@21; br:3efaa90434e1 in go:api.authMiddleware.<anon>@21; br:4ede9085ac0b in go:api.authMiddleware.<anon>@21; br:96c4e761344c in go:api.authMiddleware.<anon>@21

## Observed execution structure (deterministic; shown executions only)

```
(from 17 shown execution(s))
- go:api.authMiddleware.<anon>@21: 4 occurrence(s)
    nearest modeled caller: <root> (in 4 exec)
    runs during: <root> (in 4 exec)
- go:db/sqlc.Queries.UpdateUser: 3 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 3 exec)
    runs during: go:gapi.Server.UpdateUser (in 3 exec)
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
- go:gapi.validateUpdateUserRequest: 5 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 5 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec)
- go:token.JWTMaker.CreateToken: 2 occurrence(s)
    nearest modeled caller: <root> (in 2 exec)
    runs during: <root> (in 2 exec)
- go:token.JWTMaker.VerifyToken: 3 occurrence(s)
    nearest modeled caller: <root> (in 3 exec)
    runs during: <root> (in 3 exec)
- go:token.NewPayload: 15 occurrence(s)
    nearest modeled caller: <root> (in 1 exec), go:token.JWTMaker.CreateToken (in 2 exec), go:token.PasetoMaker.CreateToken (in 12 exec)
    runs during: <root> (in 1 exec), go:token.JWTMaker.CreateToken (in 2 exec), go:token.PasetoMaker.CreateToken (in 12 exec)
- go:token.PasetoMaker.CreateToken: 12 occurrence(s)
    nearest modeled caller: <root> (in 12 exec)
    runs during: <root> (in 12 exec)
- go:token.PasetoMaker.VerifyToken: 10 occurrence(s)
    nearest modeled caller: <root> (in 3 exec), go:api.authMiddleware.<anon>@21 (in 1 exec), go:gapi.Server.authorizeUser (in 6 exec)
    runs during: <root> (in 3 exec), go:api.authMiddleware.<anon>@21 (in 1 exec), go:gapi.Server.UpdateUser (in 6 exec), go:gapi.Server.authorizeUser (in 6 exec)
- go:token.Payload.Valid: 11 occurrence(s)
    nearest modeled caller: go:token.JWTMaker.VerifyToken (in 1 exec), go:token.PasetoMaker.VerifyToken (in 10 exec)
    runs during: go:api.authMiddleware.<anon>@21 (in 1 exec), go:gapi.Server.UpdateUser (in 6 exec), go:gapi.Server.authorizeUser (in 6 exec), go:token.JWTMaker.VerifyToken (in 1 exec), go:token.PasetoMaker.VerifyToken (in 10 exec)

inside go:api.authMiddleware.<anon>@21:
  family go:token.PasetoMaker.VerifyToken: in 1 occurrence(s), once
  family site:br:052de203d9d4: in 1 occurrence(s), once
  family site:br:3efaa90434e1: in 4 occurrence(s), once
  family site:br:4ede9085ac0b: in 3 occurrence(s), once
  family site:br:96c4e761344c: in 2 occurrence(s), once
  go:token.PasetoMaker.VerifyToken BEFORE site:br:052de203d9d4  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:3efaa90434e1 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:3efaa90434e1 BEFORE site:br:052de203d9d4  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:3efaa90434e1 BEFORE site:br:4ede9085ac0b  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:3efaa90434e1 BEFORE site:br:96c4e761344c  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:4ede9085ac0b BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:4ede9085ac0b BEFORE site:br:052de203d9d4  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:4ede9085ac0b BEFORE site:br:96c4e761344c  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:96c4e761344c BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:96c4e761344c BEFORE site:br:052de203d9d4  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside go:gapi.Server.UpdateUser:
  family go:db/sqlc.Queries.UpdateUser: in 3 occurrence(s), once
  family go:gapi.Server.authorizeUser: in 7 occurrence(s), once
  family go:gapi.convertUser: in 2 occurrence(s), once
  family go:gapi.validateUpdateUserRequest: in 5 occurrence(s), once
  family site:br:01807a7b80a2: in 4 occurrence(s), once
  family site:br:0746154f1c47: in 7 occurrence(s), once
  family site:br:17f2bce25a0f: in 3 occurrence(s), once
  family site:br:815be3bfb43a: in 3 occurrence(s), once
  family site:br:af0e24f4367b: in 5 occurrence(s), once
  family site:br:fb1ba40798cf: in 1 occurrence(s), once
  go:db/sqlc.Queries.UpdateUser BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:db/sqlc.Queries.UpdateUser BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:db/sqlc.Queries.UpdateUser BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
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
  go:gapi.validateUpdateUserRequest BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:gapi.validateUpdateUserRequest BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
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
  site:br:01807a7b80a2 BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE go:gapi.validateUpdateUserRequest  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
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
  site:br:815be3bfb43a BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:815be3bfb43a BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:815be3bfb43a BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:815be3bfb43a BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE go:db/sqlc.Queries.UpdateUser  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE go:gapi.convertUser  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:af0e24f4367b BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:af0e24f4367b BEFORE site:br:fb1ba40798cf  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

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
  family site:br:444b7eee95f8: in 5 occurrence(s), once
  family site:br:57793335771a: in 5 occurrence(s), once
  family site:br:578b58ceb4d3: in 5 occurrence(s), once
  family site:br:864c3600c3d5: in 5 occurrence(s), once
  family site:br:9558e38bf1ec: in 5 occurrence(s), once
  family site:br:f63e639d4185: in 5 occurrence(s), once
  site:br:444b7eee95f8 BEFORE site:br:578b58ceb4d3  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:444b7eee95f8 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
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
  site:br:578b58ceb4d3 BEFORE site:br:864c3600c3d5  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:578b58ceb4d3 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:9558e38bf1ec  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:864c3600c3d5 BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:9558e38bf1ec BEFORE site:br:f63e639d4185  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))

inside go:token.JWTMaker.CreateToken:
  family go:token.NewPayload: in 2 occurrence(s), once
  family site:br:d9f1e0c214f9: in 2 occurrence(s), once
  go:token.NewPayload BEFORE site:br:d9f1e0c214f9  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))

inside go:token.JWTMaker.VerifyToken:
  family go:token.Payload.Valid: in 1 occurrence(s), once
  family site:br:184d2ca72d5b: in 2 occurrence(s), once
  family site:br:46e44adad2e4: in 1 occurrence(s), once
  family site:br:8a21855c007e: in 1 occurrence(s), once
  family site:br:b95a526c7153: in 3 occurrence(s), once
  go:token.Payload.Valid BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:46e44adad2e4 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:46e44adad2e4 BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b95a526c7153 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b95a526c7153 BEFORE site:br:184d2ca72d5b  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:b95a526c7153 BEFORE site:br:46e44adad2e4  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b95a526c7153 BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside go:token.PasetoMaker.CreateToken:
  family go:token.NewPayload: in 12 occurrence(s), once
  family site:br:0713394c9923: in 12 occurrence(s), once
  go:token.NewPayload BEFORE site:br:0713394c9923  (all of the first before all of the second;
      12 occurrence(s), 12 execution(s))

inside go:token.PasetoMaker.VerifyToken:
  family go:token.Payload.Valid: in 10 occurrence(s), once
  family site:br:0607e4d952f6: in 10 occurrence(s), once
  family site:br:c7d403dfabc3: in 10 occurrence(s), once
  go:token.Payload.Valid BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      10 occurrence(s), 10 execution(s))
  site:br:0607e4d952f6 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      10 occurrence(s), 10 execution(s))
  site:br:0607e4d952f6 BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      10 occurrence(s), 10 execution(s))

inside go:token.Payload.Valid:
  family site:br:8d10f2f9b136: in 11 occurrence(s), once
  family site:br:bdb0acf90853: in 10 occurrence(s), once
  site:br:8d10f2f9b136 BEFORE site:br:bdb0acf90853  (all of the first before all of the second;
      10 occurrence(s), 10 execution(s))
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

### token.JWTMaker.CreateToken  (token/jwt_maker.go)
- site br:d9f1e0c214f9 line 29: `err != nil` | operands: err ← call:NewPayload#1 | requires: — | then exits: True, else exits: False
- call `NewPayload` line 28 requires: —
- call `jwt.NewWithClaims` line 33 requires: br:d9f1e0c214f9=F
- call `[]byte` line 34 requires: br:d9f1e0c214f9=F
- call `jwtToken.SignedString` line 34 requires: br:d9f1e0c214f9=F

### token.JWTMaker.VerifyToken  (token/jwt_maker.go)
- site br:b95a526c7153 line 49: `err != nil` | operands: err ← call:jwt.ParseWithClaims#1 | requires: — | then exits: True, else exits: False
- site br:184d2ca72d5b line 50: `errors.Is(err, jwt.ErrTokenExpired)` | operands: errors ← global:errors; err ← call:jwt.ParseWithClaims#1; jwt.ErrTokenExpired ← global:jwt.ErrTokenExpired | requires: br:b95a526c7153=T | then exits: True, else exits: False
- site br:46e44adad2e4 line 57: `!ok` | operands: ok ← call:jwt.ParseWithClaims#0.Claims | requires: br:b95a526c7153=F | then exits: True, else exits: False
- site br:8a21855c007e line 62: `err != nil` | operands: err ← call:payload.Valid | requires: br:b95a526c7153=F & br:46e44adad2e4=F | then exits: True, else exits: False
- call `jwt.ParseWithClaims` line 48 requires: —
- call `errors.Is` line 50 requires: br:b95a526c7153=T
- call `payload.Valid` line 61 requires: br:b95a526c7153=F & br:46e44adad2e4=F

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
- site br:ecd8b89da8b7 line 37: `err != nil` | operands: err ← call:uuid.NewRandom#1 | requires: — | then exits: True, else exits: False
- call `uuid.NewRandom` line 36 requires: —
- call `time.Now` line 46 requires: br:ecd8b89da8b7=F
- call `time.Now` line 47 requires: br:ecd8b89da8b7=F
- call `time.Now().Add` line 47 requires: br:ecd8b89da8b7=F

### token.Payload.Valid  (token/payload.go)
- site br:8d10f2f9b136 line 54: `payload.Type != tokenType` | operands: payload.Type ← param:payload.Type; tokenType ← param:tokenType | requires: — | then exits: True, else exits: False
- site br:bdb0acf90853 line 57: `time.Now().After(payload.ExpiredAt)` | operands: time ← global:time; payload.ExpiredAt ← param:payload.ExpiredAt | requires: br:8d10f2f9b136=F | then exits: True, else exits: False
- call `time.Now` line 57 requires: br:8d10f2f9b136=F
- call `time.Now().After` line 57 requires: br:8d10f2f9b136=F

## Observed event logs (shown tests, at head)

Calls of the listed functions in chronological order, indented by depth among them (everything else is looked through), with argument shapes and value digests, results, exits, and the observed outcome of every decision site evaluated in those calls.

```
### TestAuthMiddleware/ExpiredToken  test: passed  exits: api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call api.authMiddleware.<anon>@21(ctx=*gin.Context) [returned]
  branch br:3efaa90434e1 `?` = F
  branch br:4ede9085ac0b `?` = F
  branch br:96c4e761344c `?` = F
  call token.PasetoMaker.VerifyToken(token=string#4f1428, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
    branch br:0607e4d952f6 `err != nil` = F
    call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
      branch br:8d10f2f9b136 `payload.Type != tokenType` = F
      branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = T
    branch br:c7d403dfabc3 `err != nil` = T
  branch br:052de203d9d4 `?` = T

### TestAuthMiddleware/InvalidAuthorizationFormat  test: passed  exits: api.authMiddleware.<anon>@21 returned
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call api.authMiddleware.<anon>@21(ctx=*gin.Context) [returned]
  branch br:3efaa90434e1 `?` = F
  branch br:4ede9085ac0b `?` = T

### TestAuthMiddleware/NoAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call api.authMiddleware.<anon>@21(ctx=*gin.Context) [returned]
  branch br:3efaa90434e1 `?` = T

### TestAuthMiddleware/UnsupportedAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call api.authMiddleware.<anon>@21(ctx=*gin.Context) [returned]
  branch br:3efaa90434e1 `?` = F
  branch br:4ede9085ac0b `?` = F
  branch br:96c4e761344c `?` = T

### TestExpiredJWTToken  test: passed  exits: token.JWTMaker.VerifyToken returned-error:go:*errors.errorString; token.JWTMaker.VerifyToken.<anon>@40 returned
call token.JWTMaker.CreateToken(username=string#a6ec52, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#a6ec52, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:d9f1e0c214f9 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#047a72, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  branch br:b95a526c7153 `err != nil` = T
  branch br:184d2ca72d5b `errors.Is(err, jwt.ErrTokenExpired)` = T

### TestExpiredPasetoToken  test: passed  exits: token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#8e9b1b, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#8e9b1b, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#0b5f2d, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = T
  branch br:c7d403dfabc3 `err != nil` = T

### TestInvalidJWTTokenAlgNone  test: passed  exits: token.JWTMaker.VerifyToken returned-error:go:*errors.errorString; token.JWTMaker.VerifyToken.<anon>@40 returned-error:go:*errors.errorString
call token.NewPayload(username=string#f1c5f1, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  branch br:ecd8b89da8b7 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#f4f56a, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  branch br:b95a526c7153 `err != nil` = T
  branch br:184d2ca72d5b `errors.Is(err, jwt.ErrTokenExpired)` = F

### TestJWTMaker  test: passed  exits: token.JWTMaker.VerifyToken returned; token.JWTMaker.VerifyToken.<anon>@40 returned
call token.JWTMaker.CreateToken(username=string#5d3dd3, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5d3dd3, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:d9f1e0c214f9 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#d21de1, tokenType=token.TokenType#35ddf6) [returned]
  branch br:b95a526c7153 `err != nil` = F
  branch br:46e44adad2e4 `!ok` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:8a21855c007e `err != nil` = F

### TestPasetoMaker  test: passed  exits: token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#39b14f, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#39b14f, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#dc6e7f, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F

### TestPasetoWrongTokenType  test: passed  exits: token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#982f5e, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#982f5e, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#614b02, tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
    branch br:8d10f2f9b136 `payload.Type != tokenType` = T
  branch br:c7d403dfabc3 `err != nil` = T

### TestUpdateUserAPI/BankerCanUpdateUserInfo  test: passed  exits: gapi.Server.UpdateUser returned; token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#0df0f6, role=string#9f99e2, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#0df0f6, role=string#9f99e2, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#7740d8, tokenType=token.TokenType#35ddf6) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#9f99e2, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#914e8d) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  call db/sqlc.Queries.UpdateUser(arg0=*context.valueCtx, arg1=db.UpdateUserParams#4c1343) [returned] (stand-in, mocked)
  branch br:17f2bce25a0f `err != nil` = F
  call gapi.convertUser(user=db.User#5ba1b2) [returned]

### TestUpdateUserAPI/ExpiredToken  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#c720df, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#c720df, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#b729e2, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = T
      branch br:c7d403dfabc3 `err != nil` = T
    branch br:c71158777bce `err != nil` = T
  branch br:0746154f1c47 `err != nil` = T

### TestUpdateUserAPI/InvalidEmail  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error; token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#94e178) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#b6a6d4, tokenType=token.TokenType#35ddf6) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#94e178) [returned] -> #0dd246
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = T
  branch br:af0e24f4367b `violations != nil` = T

### TestUpdateUserAPI/NoAuthorization  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error
call gapi.Server.UpdateUser(ctx=context.backgroundCtx#2e2a50, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=context.backgroundCtx#2e2a50, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = T
  branch br:0746154f1c47 `err != nil` = T

### TestUpdateUserAPI/OK  test: passed  exits: gapi.Server.UpdateUser returned; token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#8606ed, tokenType=token.TokenType#35ddf6) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#914e8d) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  call db/sqlc.Queries.UpdateUser(arg0=*context.valueCtx, arg1=db.UpdateUserParams#4c1343) [returned] (stand-in, mocked)
  branch br:17f2bce25a0f `err != nil` = F
  call gapi.convertUser(user=db.User#5ba1b2) [returned]

### TestUpdateUserAPI/OtherDepositorCannotUpdateThisUserInfo  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error; token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#b98c9a, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#b98c9a, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#b86a0e, tokenType=token.TokenType#35ddf6) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#914e8d) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = T

### TestUpdateUserAPI/UserNotFound  test: passed  exits: gapi.Server.UpdateUser returned-error:go:*status.Error; token.PasetoMaker.VerifyToken returned
call token.PasetoMaker.CreateToken(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#c215f4, tokenType=token.TokenType#35ddf6) [returned]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
        branch br:8d10f2f9b136 `payload.Type != tokenType` = F
        branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
      branch br:c7d403dfabc3 `err != nil` = F
    branch br:c71158777bce `err != nil` = F
    call gapi.hasPermission(userRole=string#2ab61d, accessibleRoles=[]string[2]#0bd72d) [returned] -> #4026e0
      branch br:92f48828a554 `userRole == role` = F
      branch br:92f48828a554 `userRole == role` = T
    branch br:c1bc39962889 `!hasPermission(payload.Role, accessibleRoles)` = F
  branch br:0746154f1c47 `err != nil` = F
  call gapi.validateUpdateUserRequest(req=*pb.UpdateUserRequest#914e8d) [returned] -> #e96533
    branch br:57793335771a `err != nil` = F
    branch br:444b7eee95f8 `req.Password != nil` = F
    branch br:578b58ceb4d3 `req.FullName != nil` = T
    branch br:864c3600c3d5 `err != nil` = F
    branch br:9558e38bf1ec `req.Email != nil` = T
    branch br:f63e639d4185 `err != nil` = F
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  call db/sqlc.Queries.UpdateUser(arg0=*context.valueCtx, arg1=db.UpdateUserParams#4c1343) [returned-error:go:*errors.errorString] (stand-in, mocked)
  branch br:17f2bce25a0f `err != nil` = T
  branch br:fb1ba40798cf `errors.Is(err, db.ErrRecordNotFound)` = T
```

Withheld (observed, not shown): TestJWTWrongTokenType, TestUpdateUserAPI/WrongTokenType, TestAuthMiddleware/OK

## The change (git diff 7c6f92f2..97f000fe, non-test Go sources in token, gapi, api)

```diff
diff --git a/api/middleware.go b/api/middleware.go
index dfd5525..56b5ddd 100644
--- a/api/middleware.go
+++ b/api/middleware.go
@@ -42,7 +42,7 @@ func authMiddleware(tokenMaker token.Maker) gin.HandlerFunc {
 		}
 
 		accessToken := fields[1]
-		payload, err := tokenMaker.VerifyToken(accessToken)
+		payload, err := tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
 		if err != nil {
 			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
 			return
diff --git a/api/token.go b/api/token.go
index 7d7b615..7183ad7 100644
--- a/api/token.go
+++ b/api/token.go
@@ -8,6 +8,7 @@ import (
 
 	"github.com/gin-gonic/gin"
 	db "github.com/techschool/simplebank/db/sqlc"
+	"github.com/techschool/simplebank/token"
 )
 
 type renewAccessTokenRequest struct {
@@ -26,7 +27,7 @@ func (server *Server) renewAccessToken(ctx *gin.Context) {
 		return
 	}
 
-	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken)
+	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken, token.TokenTypeRefreshToken)
 	if err != nil {
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
@@ -70,6 +71,7 @@ func (server *Server) renewAccessToken(ctx *gin.Context) {
 		refreshPayload.Username,
 		refreshPayload.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
diff --git a/api/user.go b/api/user.go
index 94de476..640f3c6 100644
--- a/api/user.go
+++ b/api/user.go
@@ -8,6 +8,7 @@ import (
 	"github.com/gin-gonic/gin"
 	"github.com/google/uuid"
 	db "github.com/techschool/simplebank/db/sqlc"
+	"github.com/techschool/simplebank/token"
 	"github.com/techschool/simplebank/util"
 )
 
@@ -111,6 +112,7 @@ func (server *Server) loginUser(ctx *gin.Context) {
 		user.Username,
 		user.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
@@ -121,6 +123,7 @@ func (server *Server) loginUser(ctx *gin.Context) {
 		user.Username,
 		user.Role,
 		server.config.RefreshTokenDuration,
+		token.TokenTypeRefreshToken,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
diff --git a/gapi/authorization.go b/gapi/authorization.go
index 892467d..3c76d66 100644
--- a/gapi/authorization.go
+++ b/gapi/authorization.go
@@ -37,7 +37,7 @@ func (server *Server) authorizeUser(ctx context.Context, accessibleRoles []strin
 	}
 
 	accessToken := fields[1]
-	payload, err := server.tokenMaker.VerifyToken(accessToken)
+	payload, err := server.tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
 	if err != nil {
 		return nil, fmt.Errorf("invalid access token: %s", err)
 	}
diff --git a/gapi/rpc_create_user.go b/gapi/rpc_create_user.go
index ec87dd0..66b2ee6 100644
--- a/gapi/rpc_create_user.go
+++ b/gapi/rpc_create_user.go
@@ -50,7 +50,7 @@ func (server *Server) CreateUser(ctx context.Context, req *pb.CreateUserRequest)
 	txResult, err := server.store.CreateUserTx(ctx, arg)
 	if err != nil {
 		if db.ErrorCode(err) == db.UniqueViolation {
-			return nil, status.Errorf(codes.AlreadyExists, err.Error())
+			return nil, status.Error(codes.AlreadyExists, err.Error())
 		}
 		return nil, status.Errorf(codes.Internal, "failed to create user: %s", err)
 	}
diff --git a/gapi/rpc_login_user.go b/gapi/rpc_login_user.go
index 259ba21..139a953 100644
--- a/gapi/rpc_login_user.go
+++ b/gapi/rpc_login_user.go
@@ -6,6 +6,7 @@ import (
 
 	db "github.com/techschool/simplebank/db/sqlc"
 	"github.com/techschool/simplebank/pb"
+	"github.com/techschool/simplebank/token"
 	"github.com/techschool/simplebank/util"
 	"github.com/techschool/simplebank/val"
 	"google.golang.org/genproto/googleapis/rpc/errdetails"
@@ -37,6 +38,7 @@ func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (
 		user.Username,
 		user.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
 	)
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create access token")
@@ -46,6 +48,7 @@ func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (
 		user.Username,
 		user.Role,
 		server.config.RefreshTokenDuration,
+		token.TokenTypeRefreshToken,
 	)
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create refresh token")
diff --git a/token/jwt_maker.go b/token/jwt_maker.go
index c130dfa..59af469 100644
--- a/token/jwt_maker.go
+++ b/token/jwt_maker.go
@@ -24,8 +24,8 @@ func NewJWTMaker(secretKey string) (Maker, error) {
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, role, duration)
+func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration, tokenType)
 	if err != nil {
 		return "", payload, err
 	}
@@ -36,7 +36,7 @@ func (maker *JWTMaker) CreateToken(username string, role string, duration time.D
 }
 
 // VerifyToken checks if the token is valid or not
-func (maker *JWTMaker) VerifyToken(token string) (*Payload, error) {
+func (maker *JWTMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
 	keyFunc := func(token *jwt.Token) (interface{}, error) {
 		_, ok := token.Method.(*jwt.SigningMethodHMAC)
 		if !ok {
@@ -58,5 +58,10 @@ func (maker *JWTMaker) VerifyToken(token string) (*Payload, error) {
 		return nil, ErrInvalidToken
 	}
 
+	err = payload.Valid(tokenType)
+	if err != nil {
+		return nil, err
+	}
+
 	return payload, nil
 }
diff --git a/token/maker.go b/token/maker.go
index 9466e78..9c65fe9 100644
--- a/token/maker.go
+++ b/token/maker.go
@@ -7,8 +7,8 @@ import (
 // Maker is an interface for managing tokens
 type Maker interface {
 	// CreateToken creates a new token for a specific username and duration
-	CreateToken(username string, role string, duration time.Duration) (string, *Payload, error)
+	CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error)
 
 	// VerifyToken checks if the token is valid or not
-	VerifyToken(token string) (*Payload, error)
+	VerifyToken(token string, tokenType TokenType) (*Payload, error)
 }
diff --git a/token/paseto_maker.go b/token/paseto_maker.go
index d855837..8ee9ffc 100644
--- a/token/paseto_maker.go
+++ b/token/paseto_maker.go
@@ -29,8 +29,8 @@ func NewPasetoMaker(symmetricKey string) (Maker, error) {
 }
 
 // CreateToken creates a new token for a specific username and duration
-func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, role, duration)
+func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration, tokenType)
 	if err != nil {
 		return "", payload, err
 	}
@@ -40,7 +40,7 @@ func (maker *PasetoMaker) CreateToken(username string, role string, duration tim
 }
 
 // VerifyToken checks if the token is valid or not
-func (maker *PasetoMaker) VerifyToken(token string) (*Payload, error) {
+func (maker *PasetoMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
 	payload := &Payload{}
 
 	err := maker.paseto.Decrypt(token, maker.symmetricKey, payload, nil)
@@ -48,7 +48,7 @@ func (maker *PasetoMaker) VerifyToken(token string) (*Payload, error) {
 		return nil, ErrInvalidToken
 	}
 
-	err = payload.Valid()
+	err = payload.Valid(tokenType)
 	if err != nil {
 		return nil, err
 	}
diff --git a/token/payload.go b/token/payload.go
index 05ec639..2130681 100644
--- a/token/payload.go
+++ b/token/payload.go
@@ -14,9 +14,17 @@ var (
 	ErrExpiredToken = errors.New("token has expired")
 )
 
+type TokenType byte
+
+const (
+	TokenTypeAccessToken  = 1
+	TokenTypeRefreshToken = 2
+)
+
 // Payload contains the payload data of the token
 type Payload struct {
 	ID        uuid.UUID `json:"id"`
+	Type      TokenType `json:"token_type"`
 	Username  string    `json:"username"`
 	Role      string    `json:"role"`
 	IssuedAt  time.Time `json:"issued_at"`
@@ -24,7 +32,7 @@ type Payload struct {
 }
 
 // NewPayload creates a new token payload with a specific username and duration
-func NewPayload(username string, role string, duration time.Duration) (*Payload, error) {
+func NewPayload(username string, role string, duration time.Duration, tokenType TokenType) (*Payload, error) {
 	tokenID, err := uuid.NewRandom()
 	if err != nil {
 		return nil, err
@@ -32,6 +40,7 @@ func NewPayload(username string, role string, duration time.Duration) (*Payload,
 
 	payload := &Payload{
 		ID:        tokenID,
+		Type:      tokenType,
 		Username:  username,
 		Role:      role,
 		IssuedAt:  time.Now(),
@@ -41,7 +50,10 @@ func NewPayload(username string, role string, duration time.Duration) (*Payload,
 }
 
 // Valid checks if the token payload is valid or not
-func (payload *Payload) Valid() error {
+func (payload *Payload) Valid(tokenType TokenType) error {
+	if payload.Type != tokenType {
+		return ErrInvalidToken
+	}
 	if time.Now().After(payload.ExpiredAt) {
 		return ErrExpiredToken
 	}
```

## Source at HEAD: token/payload.go

```go
   1  package token
   2  
   3  import (
   4  	"errors"
   5  	"time"
   6  
   7  	"github.com/golang-jwt/jwt/v5"
   8  	"github.com/google/uuid"
   9  )
  10  
  11  // Different types of error returned by the VerifyToken function
  12  var (
  13  	ErrInvalidToken = errors.New("token is invalid")
  14  	ErrExpiredToken = errors.New("token has expired")
  15  )
  16  
  17  type TokenType byte
  18  
  19  const (
  20  	TokenTypeAccessToken  = 1
  21  	TokenTypeRefreshToken = 2
  22  )
  23  
  24  // Payload contains the payload data of the token
  25  type Payload struct {
  26  	ID        uuid.UUID `json:"id"`
  27  	Type      TokenType `json:"token_type"`
  28  	Username  string    `json:"username"`
  29  	Role      string    `json:"role"`
  30  	IssuedAt  time.Time `json:"issued_at"`
  31  	ExpiredAt time.Time `json:"expired_at"`
  32  }
  33  
  34  // NewPayload creates a new token payload with a specific username and duration
  35  func NewPayload(username string, role string, duration time.Duration, tokenType TokenType) (*Payload, error) {
  36  	tokenID, err := uuid.NewRandom()
  37  	if err != nil {
  38  		return nil, err
  39  	}
  40  
  41  	payload := &Payload{
  42  		ID:        tokenID,
  43  		Type:      tokenType,
  44  		Username:  username,
  45  		Role:      role,
  46  		IssuedAt:  time.Now(),
  47  		ExpiredAt: time.Now().Add(duration),
  48  	}
  49  	return payload, nil
  50  }
  51  
  52  // Valid checks if the token payload is valid or not
  53  func (payload *Payload) Valid(tokenType TokenType) error {
  54  	if payload.Type != tokenType {
  55  		return ErrInvalidToken
  56  	}
  57  	if time.Now().After(payload.ExpiredAt) {
  58  		return ErrExpiredToken
  59  	}
  60  	return nil
  61  }
  62  
  63  func (payload *Payload) GetExpirationTime() (*jwt.NumericDate, error) {
  64  	return &jwt.NumericDate{
  65  		Time: payload.ExpiredAt,
  66  	}, nil
  67  }
  68  
  69  func (payload *Payload) GetIssuedAt() (*jwt.NumericDate, error) {
  70  	return &jwt.NumericDate{
  71  		Time: payload.IssuedAt,
  72  	}, nil
  73  }
  74  
  75  func (payload *Payload) GetNotBefore() (*jwt.NumericDate, error) {
  76  	return &jwt.NumericDate{
  77  		Time: payload.IssuedAt,
  78  	}, nil
  79  }
  80  
  81  func (payload *Payload) GetIssuer() (string, error) {
  82  	return "", nil
  83  }
  84  
  85  func (payload *Payload) GetSubject() (string, error) {
  86  	return "", nil
  87  }
  88  
  89  func (payload *Payload) GetAudience() (jwt.ClaimStrings, error) {
  90  	return jwt.ClaimStrings{}, nil
  91  }
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
  32  func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
  33  	payload, err := NewPayload(username, role, duration, tokenType)
  34  	if err != nil {
  35  		return "", payload, err
  36  	}
  37  
  38  	token, err := maker.paseto.Encrypt(maker.symmetricKey, payload, nil)
  39  	return token, payload, err
  40  }
  41  
  42  // VerifyToken checks if the token is valid or not
  43  func (maker *PasetoMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
  44  	payload := &Payload{}
  45  
  46  	err := maker.paseto.Decrypt(token, maker.symmetricKey, payload, nil)
  47  	if err != nil {
  48  		return nil, ErrInvalidToken
  49  	}
  50  
  51  	err = payload.Valid(tokenType)
  52  	if err != nil {
  53  		return nil, err
  54  	}
  55  
  56  	return payload, nil
  57  }
```

## Source at HEAD: token/jwt_maker.go

```go
   1  package token
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"time"
   7  
   8  	"github.com/golang-jwt/jwt/v5"
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
  27  func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
  28  	payload, err := NewPayload(username, role, duration, tokenType)
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
  39  func (maker *JWTMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
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
  50  		if errors.Is(err, jwt.ErrTokenExpired) {
  51  			return nil, ErrExpiredToken
  52  		}
  53  		return nil, ErrInvalidToken
  54  	}
  55  
  56  	payload, ok := jwtToken.Claims.(*Payload)
  57  	if !ok {
  58  		return nil, ErrInvalidToken
  59  	}
  60  
  61  	err = payload.Valid(tokenType)
  62  	if err != nil {
  63  		return nil, err
  64  	}
  65  
  66  	return payload, nil
  67  }
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
  40  	payload, err := server.tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
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

## Source at HEAD: api/middleware.go

```go
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"net/http"
   7  	"strings"
   8  
   9  	"github.com/gin-gonic/gin"
  10  	"github.com/techschool/simplebank/token"
  11  )
  12  
  13  const (
  14  	authorizationHeaderKey  = "authorization"
  15  	authorizationTypeBearer = "bearer"
  16  	authorizationPayloadKey = "authorization_payload"
  17  )
  18  
  19  // AuthMiddleware creates a gin middleware for authorization
  20  func authMiddleware(tokenMaker token.Maker) gin.HandlerFunc {
  21  	return func(ctx *gin.Context) {
  22  		authorizationHeader := ctx.GetHeader(authorizationHeaderKey)
  23  
  24  		if len(authorizationHeader) == 0 {
  25  			err := errors.New("authorization header is not provided")
  26  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  27  			return
  28  		}
  29  
  30  		fields := strings.Fields(authorizationHeader)
  31  		if len(fields) < 2 {
  32  			err := errors.New("invalid authorization header format")
  33  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  34  			return
  35  		}
  36  
  37  		authorizationType := strings.ToLower(fields[0])
  38  		if authorizationType != authorizationTypeBearer {
  39  			err := fmt.Errorf("unsupported authorization type %s", authorizationType)
  40  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  41  			return
  42  		}
  43  
  44  		accessToken := fields[1]
  45  		payload, err := tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
  46  		if err != nil {
  47  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  48  			return
  49  		}
  50  
  51  		ctx.Set(authorizationPayloadKey, payload)
  52  		ctx.Next()
  53  	}
  54  }
```

## Source at HEAD: api/token.go

```go
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
  11  	"github.com/techschool/simplebank/token"
  12  )
  13  
  14  type renewAccessTokenRequest struct {
  15  	RefreshToken string `json:"refresh_token" binding:"required"`
  16  }
  17  
  18  type renewAccessTokenResponse struct {
  19  	AccessToken          string    `json:"access_token"`
  20  	AccessTokenExpiresAt time.Time `json:"access_token_expires_at"`
  21  }
  22  
  23  func (server *Server) renewAccessToken(ctx *gin.Context) {
  24  	var req renewAccessTokenRequest
  25  	if err := ctx.ShouldBindJSON(&req); err != nil {
  26  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  27  		return
  28  	}
  29  
  30  	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken, token.TokenTypeRefreshToken)
  31  	if err != nil {
  32  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  33  		return
  34  	}
  35  
  36  	session, err := server.store.GetSession(ctx, refreshPayload.ID)
  37  	if err != nil {
  38  		if errors.Is(err, db.ErrRecordNotFound) {
  39  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  40  			return
  41  		}
  42  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  43  		return
  44  	}
  45  
  46  	if session.IsBlocked {
  47  		err := fmt.Errorf("blocked session")
  48  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  49  		return
  50  	}
  51  
  52  	if session.Username != refreshPayload.Username {
  53  		err := fmt.Errorf("incorrect session user")
  54  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  55  		return
  56  	}
  57  
  58  	if session.RefreshToken != req.RefreshToken {
  59  		err := fmt.Errorf("mismatched session token")
  60  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  61  		return
  62  	}
  63  
  64  	if time.Now().After(session.ExpiresAt) {
  65  		err := fmt.Errorf("expired session")
  66  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  67  		return
  68  	}
  69  
  70  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
  71  		refreshPayload.Username,
  72  		refreshPayload.Role,
  73  		server.config.AccessTokenDuration,
  74  		token.TokenTypeAccessToken,
  75  	)
  76  	if err != nil {
  77  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  78  		return
  79  	}
  80  
  81  	rsp := renewAccessTokenResponse{
  82  		AccessToken:          accessToken,
  83  		AccessTokenExpiresAt: accessPayload.ExpiredAt,
  84  	}
  85  	ctx.JSON(http.StatusOK, rsp)
  86  }
```

## Source at HEAD: token/paseto_maker_test.go

```go
   1  package token
   2  
   3  import (
   4  	"testing"
   5  	"time"
   6  
   7  	"github.com/stretchr/testify/require"
   8  	"github.com/techschool/simplebank/util"
   9  )
  10  
  11  func TestPasetoMaker(t *testing.T) {
  12  	maker, err := NewPasetoMaker(util.RandomString(32))
  13  	require.NoError(t, err)
  14  
  15  	username := util.RandomOwner()
  16  	role := util.DepositorRole
  17  	duration := time.Minute
  18  
  19  	issuedAt := time.Now()
  20  	expiredAt := issuedAt.Add(duration)
  21  
  22  	token, payload, err := maker.CreateToken(username, role, duration, TokenTypeAccessToken)
  23  	require.NoError(t, err)
  24  	require.NotEmpty(t, token)
  25  	require.NotEmpty(t, payload)
  26  
  27  	payload, err = maker.VerifyToken(token, TokenTypeAccessToken)
  28  	require.NoError(t, err)
  29  	require.NotEmpty(t, token)
  30  
  31  	require.NotZero(t, payload.ID)
  32  	require.Equal(t, username, payload.Username)
  33  	require.Equal(t, role, payload.Role)
  34  	require.WithinDuration(t, issuedAt, payload.IssuedAt, time.Second)
  35  	require.WithinDuration(t, expiredAt, payload.ExpiredAt, time.Second)
  36  }
  37  
  38  func TestExpiredPasetoToken(t *testing.T) {
  39  	maker, err := NewPasetoMaker(util.RandomString(32))
  40  	require.NoError(t, err)
  41  
  42  	token, payload, err := maker.CreateToken(util.RandomOwner(), util.DepositorRole, -time.Minute, TokenTypeAccessToken)
  43  	require.NoError(t, err)
  44  	require.NotEmpty(t, token)
  45  	require.NotEmpty(t, payload)
  46  
  47  	payload, err = maker.VerifyToken(token, TokenTypeAccessToken)
  48  	require.Error(t, err)
  49  	require.EqualError(t, err, ErrExpiredToken.Error())
  50  	require.Nil(t, payload)
  51  }
  52  
  53  func TestPasetoWrongTokenType(t *testing.T) {
  54  	maker, err := NewPasetoMaker(util.RandomString(32))
  55  	require.NoError(t, err)
  56  
  57  	token, payload, err := maker.CreateToken(util.RandomOwner(), util.DepositorRole, time.Minute, TokenTypeAccessToken)
  58  	require.NoError(t, err)
  59  	require.NotEmpty(t, token)
  60  	require.NotEmpty(t, payload)
  61  
  62  	payload, err = maker.VerifyToken(token, TokenTypeRefreshToken)
  63  	require.Error(t, err)
  64  	require.EqualError(t, err, ErrInvalidToken.Error())
  65  	require.Nil(t, payload)
  66  }
```

## Source at HEAD: token/jwt_maker_test.go

```go
   1  package token
   2  
   3  import (
   4  	"testing"
   5  	"time"
   6  
   7  	"github.com/golang-jwt/jwt/v5"
   8  	"github.com/stretchr/testify/require"
   9  	"github.com/techschool/simplebank/util"
  10  )
  11  
  12  func TestJWTMaker(t *testing.T) {
  13  	maker, err := NewJWTMaker(util.RandomString(32))
  14  	require.NoError(t, err)
  15  
  16  	username := util.RandomOwner()
  17  	role := util.DepositorRole
  18  	duration := time.Minute
  19  
  20  	issuedAt := time.Now()
  21  	expiredAt := issuedAt.Add(duration)
  22  
  23  	token, payload, err := maker.CreateToken(username, role, duration, TokenTypeAccessToken)
  24  	require.NoError(t, err)
  25  	require.NotEmpty(t, token)
  26  	require.NotEmpty(t, payload)
  27  
  28  	payload, err = maker.VerifyToken(token, TokenTypeAccessToken)
  29  	require.NoError(t, err)
  30  	require.NotEmpty(t, token)
  31  
  32  	require.NotZero(t, payload.ID)
  33  	require.Equal(t, username, payload.Username)
  34  	require.Equal(t, role, payload.Role)
  35  	require.WithinDuration(t, issuedAt, payload.IssuedAt, time.Second)
  36  	require.WithinDuration(t, expiredAt, payload.ExpiredAt, time.Second)
  37  }
  38  
  39  func TestExpiredJWTToken(t *testing.T) {
  40  	maker, err := NewJWTMaker(util.RandomString(32))
  41  	require.NoError(t, err)
  42  
  43  	token, payload, err := maker.CreateToken(util.RandomOwner(), util.DepositorRole, -time.Minute, TokenTypeAccessToken)
  44  	require.NoError(t, err)
  45  	require.NotEmpty(t, token)
  46  	require.NotEmpty(t, payload)
  47  
  48  	payload, err = maker.VerifyToken(token, TokenTypeAccessToken)
  49  	require.Error(t, err)
  50  	require.EqualError(t, err, ErrExpiredToken.Error())
  51  	require.Nil(t, payload)
  52  }
  53  
  54  func TestInvalidJWTTokenAlgNone(t *testing.T) {
  55  	payload, err := NewPayload(util.RandomOwner(), util.DepositorRole, time.Minute, TokenTypeAccessToken)
  56  	require.NoError(t, err)
  57  
  58  	jwtToken := jwt.NewWithClaims(jwt.SigningMethodNone, payload)
  59  	token, err := jwtToken.SignedString(jwt.UnsafeAllowNoneSignatureType)
  60  	require.NoError(t, err)
  61  
  62  	maker, err := NewJWTMaker(util.RandomString(32))
  63  	require.NoError(t, err)
  64  
  65  	payload, err = maker.VerifyToken(token, TokenTypeAccessToken)
  66  	require.Error(t, err)
  67  	require.EqualError(t, err, ErrInvalidToken.Error())
  68  	require.Nil(t, payload)
  69  }
  70  
  71  func TestJWTWrongTokenType(t *testing.T) {
  72  	maker, err := NewJWTMaker(util.RandomString(32))
  73  	require.NoError(t, err)
  74  
  75  	token, payload, err := maker.CreateToken(util.RandomOwner(), util.DepositorRole, time.Minute, TokenTypeAccessToken)
  76  	require.NoError(t, err)
  77  	require.NotEmpty(t, token)
  78  	require.NotEmpty(t, payload)
  79  
  80  	payload, err = maker.VerifyToken(token, TokenTypeRefreshToken)
  81  	require.Error(t, err)
  82  	require.EqualError(t, err, ErrInvalidToken.Error())
  83  	require.Nil(t, payload)
  84  }
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
  70  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute, token.TokenTypeAccessToken)
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
 115  				return newContextWithBearerToken(t, tokenMaker, banker.Username, banker.Role, time.Minute, token.TokenTypeAccessToken)
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
 139  				return newContextWithBearerToken(t, tokenMaker, other.Username, other.Role, time.Minute, token.TokenTypeAccessToken)
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
 162  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute, token.TokenTypeAccessToken)
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
 184  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute, token.TokenTypeAccessToken)
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
 206  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, -time.Minute, token.TokenTypeAccessToken)
 207  			},
 208  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 209  				require.Error(t, err)
 210  				st, ok := status.FromError(err)
 211  				require.True(t, ok)
 212  				require.Equal(t, codes.Unauthenticated, st.Code())
 213  			},
 214  		},
 215  		{
 216  			name: "WrongTokenType",
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
 228  				return newContextWithBearerToken(t, tokenMaker, user.Username, user.Role, time.Minute, token.TokenTypeRefreshToken)
 229  			},
 230  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 231  				require.Error(t, err)
 232  				st, ok := status.FromError(err)
 233  				require.True(t, ok)
 234  				require.Equal(t, codes.Unauthenticated, st.Code())
 235  			},
 236  		},
 237  		{
 238  			name: "NoAuthorization",
 239  			req: &pb.UpdateUserRequest{
 240  				Username: user.Username,
 241  				FullName: &newName,
 242  				Email:    &newEmail,
 243  			},
 244  			buildStubs: func(store *mockdb.MockStore) {
 245  				store.EXPECT().
 246  					UpdateUser(gomock.Any(), gomock.Any()).
 247  					Times(0)
 248  			},
 249  			buildContext: func(t *testing.T, tokenMaker token.Maker) context.Context {
 250  				return context.Background()
 251  			},
 252  			checkResponse: func(t *testing.T, res *pb.UpdateUserResponse, err error) {
 253  				require.Error(t, err)
 254  				st, ok := status.FromError(err)
 255  				require.True(t, ok)
 256  				require.Equal(t, codes.Unauthenticated, st.Code())
 257  			},
 258  		},
 259  	}
 260  
 261  	for i := range testCases {
 262  		tc := testCases[i]
 263  
 264  		t.Run(tc.name, func(t *testing.T) {
 265  			storeCtrl := gomock.NewController(t)
 266  			defer storeCtrl.Finish()
 267  			store := mockdb.NewMockStore(storeCtrl)
 268  
 269  			tc.buildStubs(store)
 270  			server := newTestServer(t, store, nil)
 271  
 272  			ctx := tc.buildContext(t, server.tokenMaker)
 273  			res, err := server.UpdateUser(ctx, tc.req)
 274  			tc.checkResponse(t, res, err)
 275  		})
 276  	}
 277  }
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
  29  func newContextWithBearerToken(t *testing.T, tokenMaker token.Maker, username string, role string, duration time.Duration, tokenType token.TokenType) context.Context {
  30  	accessToken, _, err := tokenMaker.CreateToken(username, role, duration, tokenType)
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

## Source at HEAD: api/middleware_test.go

```go
   1  package api
   2  
   3  import (
   4  	"fmt"
   5  	"net/http"
   6  	"net/http/httptest"
   7  	"testing"
   8  	"time"
   9  
  10  	"github.com/gin-gonic/gin"
  11  	"github.com/stretchr/testify/require"
  12  	"github.com/techschool/simplebank/token"
  13  	"github.com/techschool/simplebank/util"
  14  )
  15  
  16  func addAuthorization(
  17  	t *testing.T,
  18  	request *http.Request,
  19  	tokenMaker token.Maker,
  20  	authorizationType string,
  21  	username string,
  22  	role string,
  23  	duration time.Duration,
  24  ) {
  25  	token, payload, err := tokenMaker.CreateToken(username, role, duration, token.TokenTypeAccessToken)
  26  	require.NoError(t, err)
  27  	require.NotEmpty(t, payload)
  28  
  29  	authorizationHeader := fmt.Sprintf("%s %s", authorizationType, token)
  30  	request.Header.Set(authorizationHeaderKey, authorizationHeader)
  31  }
  32  
  33  func TestAuthMiddleware(t *testing.T) {
  34  	username := util.RandomOwner()
  35  	role := util.DepositorRole
  36  
  37  	testCases := []struct {
  38  		name          string
  39  		setupAuth     func(t *testing.T, request *http.Request, tokenMaker token.Maker)
  40  		checkResponse func(t *testing.T, recorder *httptest.ResponseRecorder)
  41  	}{
  42  		{
  43  			name: "OK",
  44  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  45  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, username, role, time.Minute)
  46  			},
  47  			checkResponse: func(t *testing.T, recorder *httptest.ResponseRecorder) {
  48  				require.Equal(t, http.StatusOK, recorder.Code)
  49  			},
  50  		},
  51  		{
  52  			name: "NoAuthorization",
  53  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  54  			},
  55  			checkResponse: func(t *testing.T, recorder *httptest.ResponseRecorder) {
  56  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
  57  			},
  58  		},
  59  		{
  60  			name: "UnsupportedAuthorization",
  61  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  62  				addAuthorization(t, request, tokenMaker, "unsupported", username, role, time.Minute)
  63  			},
  64  			checkResponse: func(t *testing.T, recorder *httptest.ResponseRecorder) {
  65  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
  66  			},
  67  		},
  68  		{
  69  			name: "InvalidAuthorizationFormat",
  70  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  71  				addAuthorization(t, request, tokenMaker, "", username, role, time.Minute)
  72  			},
  73  			checkResponse: func(t *testing.T, recorder *httptest.ResponseRecorder) {
  74  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
  75  			},
  76  		},
  77  		{
  78  			name: "ExpiredToken",
  79  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  80  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, username, role, -time.Minute)
  81  			},
  82  			checkResponse: func(t *testing.T, recorder *httptest.ResponseRecorder) {
  83  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
  84  			},
  85  		},
  86  	}
  87  
  88  	for i := range testCases {
  89  		tc := testCases[i]
  90  
  91  		t.Run(tc.name, func(t *testing.T) {
  92  			server := newTestServer(t, nil)
  93  			authPath := "/auth"
  94  			server.router.GET(
  95  				authPath,
  96  				authMiddleware(server.tokenMaker),
  97  				func(ctx *gin.Context) {
  98  					ctx.JSON(http.StatusOK, gin.H{})
  99  				},
 100  			)
 101  
 102  			recorder := httptest.NewRecorder()
 103  			request, err := http.NewRequest(http.MethodGet, authPath, nil)
 104  			require.NoError(t, err)
 105  
 106  			tc.setupAuth(t, request, server.tokenMaker)
 107  			server.router.ServeHTTP(recorder, request)
 108  			tc.checkResponse(t, recorder)
 109  		})
 110  	}
 111  }
```
