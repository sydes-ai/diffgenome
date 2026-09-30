# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is git diff 7c6f92f2bc5dd7ffe30552bd2fe9699de06b5512..97f000fe58ad01a0774179ffa8884ac7784cf263 in the repository simplebank (runtime
go/test). Changed symbols: api.Server.loginUser, api.Server.renewAccessToken, api.authMiddleware.<anon>@21, gapi.Server.CreateUser, gapi.Server.LoginUser, gapi.Server.authorizeUser, token.JWTMaker.CreateToken, token.JWTMaker.VerifyToken, token.Maker, token.NewPayload, token.PasetoMaker.CreateToken, token.PasetoMaker.VerifyToken, token.Payload, token.Payload.Valid, token.TokenType.

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

- br:eb7b1a216152 go:api.Server.loginUser line 90: `err != nil`
- br:84d886a24efe go:api.Server.loginUser line 96: `err != nil`
- br:e540ee8e596a go:api.Server.loginUser line 97: `errors.Is(err, db.ErrRecordNotFound)`
- br:8ac57f80bf1d go:api.Server.loginUser line 106: `err != nil`
- br:b2bb97f7167b go:api.Server.loginUser line 117: `err != nil`
- br:81d23a5f3d1d go:api.Server.loginUser line 128: `err != nil`
- br:7fe5569cfdac go:api.Server.loginUser line 142: `err != nil`
- br:51914597d4b2 go:api.Server.renewAccessToken line 25: `err != nil`   (not evaluated by any test)
- br:b98712eb46d4 go:api.Server.renewAccessToken line 31: `err != nil`   (not evaluated by any test)
- br:d2add7aaa3bb go:api.Server.renewAccessToken line 37: `err != nil`   (not evaluated by any test)
- br:c91282863028 go:api.Server.renewAccessToken line 38: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated by any test)
- br:4c153bb03d9c go:api.Server.renewAccessToken line 46: `session.IsBlocked`   (not evaluated by any test)
- br:58d817da41f5 go:api.Server.renewAccessToken line 52: `session.Username != refreshPayload.Username`   (not evaluated by any test)
- br:48d3578e9a44 go:api.Server.renewAccessToken line 58: `session.RefreshToken != req.RefreshToken`   (not evaluated by any test)
- br:7b9ae91490eb go:api.Server.renewAccessToken line 64: `time.Now().After(session.ExpiresAt)`   (not evaluated by any test)
- br:65b3034c3f05 go:api.Server.renewAccessToken line 76: `err != nil`   (not evaluated by any test)
- br:bb32884fc4f0 go:gapi.Server.CreateUser line 20: `violations != nil`   (not evaluated by any test)
- br:be27f218e30f go:gapi.Server.CreateUser line 25: `err != nil`   (not evaluated by any test)
- br:086cd7460869 go:gapi.Server.CreateUser line 51: `err != nil`   (not evaluated by any test)
- br:f9551788eb8d go:gapi.Server.CreateUser line 52: `db.ErrorCode(err) == db.UniqueViolation`   (not evaluated by any test)
- br:76bc8d02ae40 go:gapi.Server.LoginUser line 20: `violations != nil`   (not evaluated by any test)
- br:bbafcfbd5eed go:gapi.Server.LoginUser line 25: `err != nil`   (not evaluated by any test)
- br:5524c0c4b7f1 go:gapi.Server.LoginUser line 26: `errors.Is(err, db.ErrRecordNotFound)`   (not evaluated by any test)
- br:7b2947a85e0c go:gapi.Server.LoginUser line 33: `err != nil`   (not evaluated by any test)
- br:85b863c14186 go:gapi.Server.LoginUser line 43: `err != nil`   (not evaluated by any test)
- br:791afc927393 go:gapi.Server.LoginUser line 53: `err != nil`   (not evaluated by any test)
- br:65d9ca0b3d0c go:gapi.Server.LoginUser line 67: `err != nil`   (not evaluated by any test)
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

## Observed execution structure (deterministic)

```
(from 40 shown execution(s))
- go:api.Server.createAccount: 3 occurrence(s)
    nearest modeled caller: <root> (in 3 exec)
    runs during: <root> (in 3 exec)
- go:api.Server.createTransfer: 2 occurrence(s)
    nearest modeled caller: <root> (in 2 exec)
    runs during: <root> (in 2 exec)
- go:api.Server.getAccount: 5 occurrence(s)
    nearest modeled caller: <root> (in 5 exec)
    runs during: <root> (in 5 exec)
- go:api.Server.listAccounts: 4 occurrence(s)
    nearest modeled caller: <root> (in 4 exec)
    runs during: <root> (in 4 exec)
- go:api.Server.loginUser: 5 occurrence(s)
    nearest modeled caller: <root> (in 5 exec)
    runs during: <root> (in 5 exec)
- go:api.errorResponse: 22 occurrence(s)
    nearest modeled caller: <root> (in 7 exec), go:api.Server.createAccount (in 2 exec), go:api.Server.createTransfer (in 2 exec), go:api.Server.getAccount (in 4 exec), go:api.Server.listAccounts (in 3 exec), go:api.Server.loginUser (in 4 exec)
    runs during: <root> (in 7 exec), go:api.Server.createAccount (in 2 exec), go:api.Server.createTransfer (in 2 exec), go:api.Server.getAccount (in 4 exec), go:api.Server.listAccounts (in 3 exec), go:api.Server.loginUser (in 4 exec)
- go:api.newUserResponse: 1 occurrence(s)
    nearest modeled caller: go:api.Server.loginUser (in 1 exec)
    runs during: go:api.Server.loginUser (in 1 exec)
- go:gapi.Server.UpdateUser: 6 occurrence(s)
    nearest modeled caller: <root> (in 6 exec)
    runs during: <root> (in 6 exec)
- go:gapi.Server.authorizeUser: 6 occurrence(s)
    nearest modeled caller: go:gapi.Server.UpdateUser (in 6 exec)
    runs during: go:gapi.Server.UpdateUser (in 6 exec)
- go:gapi.hasPermission: 3 occurrence(s)
    nearest modeled caller: go:gapi.Server.authorizeUser (in 3 exec)
    runs during: go:gapi.Server.UpdateUser (in 3 exec), go:gapi.Server.authorizeUser (in 3 exec)
- go:token.JWTMaker.CreateToken: 3 occurrence(s)
    nearest modeled caller: <root> (in 3 exec)
    runs during: <root> (in 3 exec)
- go:token.JWTMaker.VerifyToken: 4 occurrence(s)
    nearest modeled caller: <root> (in 4 exec)
    runs during: <root> (in 4 exec)
- go:token.JWTMaker.VerifyToken.<anon>@40: 4 occurrence(s)
    nearest modeled caller: go:token.JWTMaker.VerifyToken (in 4 exec)
    runs during: go:token.JWTMaker.VerifyToken (in 4 exec)
- go:token.NewPayload: 32 occurrence(s)
    nearest modeled caller: <root> (in 1 exec), go:token.JWTMaker.CreateToken (in 3 exec), go:token.PasetoMaker.CreateToken (in 27 exec)
    runs during: <root> (in 1 exec), go:api.Server.loginUser (in 1 exec), go:token.JWTMaker.CreateToken (in 3 exec), go:token.PasetoMaker.CreateToken (in 27 exec)
- go:token.PasetoMaker.CreateToken: 28 occurrence(s)
    nearest modeled caller: <root> (in 26 exec), go:api.Server.loginUser (in 1 exec)
    runs during: <root> (in 26 exec), go:api.Server.loginUser (in 1 exec)
- go:token.PasetoMaker.VerifyToken: 24 occurrence(s)
    nearest modeled caller: <root> (in 19 exec), go:gapi.Server.authorizeUser (in 5 exec)
    runs during: <root> (in 19 exec), go:gapi.Server.UpdateUser (in 5 exec), go:gapi.Server.authorizeUser (in 5 exec)
- go:token.Payload.GetExpirationTime: 3 occurrence(s)
    nearest modeled caller: go:token.JWTMaker.VerifyToken (in 3 exec)
    runs during: go:token.JWTMaker.VerifyToken (in 3 exec)
- go:token.Payload.GetNotBefore: 3 occurrence(s)
    nearest modeled caller: go:token.JWTMaker.VerifyToken (in 3 exec)
    runs during: go:token.JWTMaker.VerifyToken (in 3 exec)
- go:token.Payload.Valid: 26 occurrence(s)
    nearest modeled caller: go:token.JWTMaker.VerifyToken (in 2 exec), go:token.PasetoMaker.VerifyToken (in 24 exec)
    runs during: go:gapi.Server.UpdateUser (in 5 exec), go:gapi.Server.authorizeUser (in 5 exec), go:token.JWTMaker.VerifyToken (in 2 exec), go:token.PasetoMaker.VerifyToken (in 24 exec)
- go:util.CheckPassword: 2 occurrence(s)
    nearest modeled caller: go:api.Server.loginUser (in 2 exec)
    runs during: go:api.Server.loginUser (in 2 exec)

inside go:api.Server.createAccount:
  family go:api.errorResponse: in 2 occurrence(s), once
  family site:br:2edcfe25beec: in 2 occurrence(s), once
  family site:br:ce254cb89878: in 1 occurrence(s), once
  family site:br:d82f37a90a3d: in 3 occurrence(s), once
  site:br:2edcfe25beec BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:2edcfe25beec BEFORE site:br:ce254cb89878  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:ce254cb89878 BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:d82f37a90a3d BEFORE go:api.errorResponse  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:d82f37a90a3d BEFORE site:br:2edcfe25beec  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:d82f37a90a3d BEFORE site:br:ce254cb89878  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside go:api.Server.createTransfer:
  family go:api.errorResponse: in 2 occurrence(s), once
  family site:br:60a4c43004b3: in 2 occurrence(s), once
  family site:br:896fb396ec78: in 2 occurrence(s), once
  go:api.errorResponse BEFORE site:br:60a4c43004b3  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:896fb396ec78 BEFORE go:api.errorResponse  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:896fb396ec78 BEFORE site:br:60a4c43004b3  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))

inside go:api.Server.getAccount:
  family go:api.errorResponse: in 4 occurrence(s), once
  family site:br:4831b305602f: in 2 occurrence(s), once
  family site:br:d8dc32e00682: in 5 occurrence(s), once
  family site:br:e5925acb2501: in 2 occurrence(s), once
  family site:br:ee83f4152f4f: in 4 occurrence(s), once
  site:br:4831b305602f BEFORE go:api.errorResponse  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:d8dc32e00682 BEFORE go:api.errorResponse  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:d8dc32e00682 BEFORE site:br:4831b305602f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:d8dc32e00682 BEFORE site:br:e5925acb2501  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:d8dc32e00682 BEFORE site:br:ee83f4152f4f  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:e5925acb2501 BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:ee83f4152f4f BEFORE go:api.errorResponse  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:ee83f4152f4f BEFORE site:br:4831b305602f  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:ee83f4152f4f BEFORE site:br:e5925acb2501  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))

inside go:api.Server.listAccounts:
  family go:api.errorResponse: in 3 occurrence(s), once
  family site:br:44fa436929dc: in 2 occurrence(s), once
  family site:br:5264ed92d2dc: in 4 occurrence(s), once
  site:br:44fa436929dc BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:5264ed92d2dc BEFORE go:api.errorResponse  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:5264ed92d2dc BEFORE site:br:44fa436929dc  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))

inside go:api.Server.loginUser:
  family go:api.errorResponse: in 4 occurrence(s), once
  family go:api.newUserResponse: in 1 occurrence(s), once
  family go:token.PasetoMaker.CreateToken: in 1 occurrence(s), repeated (up to 2 in one occurrence)
  family go:util.CheckPassword: in 2 occurrence(s), once
  family site:br:7fe5569cfdac: in 1 occurrence(s), once
  family site:br:81d23a5f3d1d: in 1 occurrence(s), once
  family site:br:84d886a24efe: in 4 occurrence(s), once
  family site:br:8ac57f80bf1d: in 2 occurrence(s), once
  family site:br:b2bb97f7167b: in 1 occurrence(s), once
  family site:br:e540ee8e596a: in 2 occurrence(s), once
  family site:br:eb7b1a216152: in 5 occurrence(s), once
  go:token.PasetoMaker.CreateToken BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:token.PasetoMaker.CreateToken BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:token.PasetoMaker.CreateToken BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE go:token.PasetoMaker.CreateToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:util.CheckPassword BEFORE site:br:8ac57f80bf1d  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:util.CheckPassword BEFORE site:br:b2bb97f7167b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:7fe5569cfdac BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:81d23a5f3d1d BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:81d23a5f3d1d BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE go:api.errorResponse  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:84d886a24efe BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE go:token.PasetoMaker.CreateToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE go:util.CheckPassword  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:84d886a24efe BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE site:br:8ac57f80bf1d  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:84d886a24efe BEFORE site:br:b2bb97f7167b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:84d886a24efe BEFORE site:br:e540ee8e596a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:8ac57f80bf1d BEFORE go:api.errorResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:8ac57f80bf1d BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:8ac57f80bf1d BEFORE go:token.PasetoMaker.CreateToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:8ac57f80bf1d BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:8ac57f80bf1d BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:8ac57f80bf1d BEFORE site:br:b2bb97f7167b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b2bb97f7167b BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b2bb97f7167b BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:b2bb97f7167b BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:e540ee8e596a BEFORE go:api.errorResponse  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:eb7b1a216152 BEFORE go:api.errorResponse  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:eb7b1a216152 BEFORE go:api.newUserResponse  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:eb7b1a216152 BEFORE go:token.PasetoMaker.CreateToken  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:eb7b1a216152 BEFORE go:util.CheckPassword  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:7fe5569cfdac  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:81d23a5f3d1d  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:84d886a24efe  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:8ac57f80bf1d  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:b2bb97f7167b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:eb7b1a216152 BEFORE site:br:e540ee8e596a  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  REPEATED REGION: go:token.PasetoMaker.CreateToken, site:br:b2bb97f7167b
    each repetition starts with go:token.PasetoMaker.CreateToken (up to 2 repetitions in one occurrence); inside one:
      go:token.PasetoMaker.CreateToken BEFORE site:br:b2bb97f7167b  (1 repetition(s))

inside go:gapi.Server.UpdateUser:
  family go:gapi.Server.authorizeUser: in 6 occurrence(s), once
  family site:br:01807a7b80a2: in 2 occurrence(s), once
  family site:br:0746154f1c47: in 6 occurrence(s), once
  family site:br:17f2bce25a0f: in 1 occurrence(s), once
  family site:br:815be3bfb43a: in 1 occurrence(s), once
  family site:br:af0e24f4367b: in 3 occurrence(s), once
  go:gapi.Server.authorizeUser BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:0746154f1c47  (all of the first before all of the second;
      6 occurrence(s), 6 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:gapi.Server.authorizeUser BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:01807a7b80a2 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:0746154f1c47 BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:0746154f1c47 BEFORE site:br:af0e24f4367b  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:815be3bfb43a BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE site:br:01807a7b80a2  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:af0e24f4367b BEFORE site:br:17f2bce25a0f  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:af0e24f4367b BEFORE site:br:815be3bfb43a  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside go:gapi.Server.authorizeUser:
  family go:gapi.hasPermission: in 3 occurrence(s), once
  family go:token.PasetoMaker.VerifyToken: in 5 occurrence(s), once
  family site:br:2e2f712d6301: in 5 occurrence(s), once
  family site:br:4393757b65d7: in 5 occurrence(s), once
  family site:br:a572eeb6a4c8: in 5 occurrence(s), once
  family site:br:c1bc39962889: in 3 occurrence(s), once
  family site:br:c71158777bce: in 5 occurrence(s), once
  family site:br:e3505bc4c4b9: in 6 occurrence(s), once
  go:gapi.hasPermission BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.PasetoMaker.VerifyToken BEFORE site:br:c71158777bce  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2e2f712d6301 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:2e2f712d6301 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:2e2f712d6301 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:4393757b65d7 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:4393757b65d7 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:4393757b65d7 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:4393757b65d7 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:a572eeb6a4c8 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:a572eeb6a4c8 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:c71158777bce BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:c71158777bce BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:gapi.hasPermission  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:e3505bc4c4b9 BEFORE go:token.PasetoMaker.VerifyToken  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:2e2f712d6301  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:4393757b65d7  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:a572eeb6a4c8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c1bc39962889  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  site:br:e3505bc4c4b9 BEFORE site:br:c71158777bce  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))

inside go:token.JWTMaker.CreateToken:
  family go:token.NewPayload: in 3 occurrence(s), once
  family site:br:d9f1e0c214f9: in 3 occurrence(s), once
  go:token.NewPayload BEFORE site:br:d9f1e0c214f9  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))

inside go:token.JWTMaker.VerifyToken:
  family go:token.JWTMaker.VerifyToken.<anon>@40: in 4 occurrence(s), once
  family go:token.Payload.GetExpirationTime: in 3 occurrence(s), once
  family go:token.Payload.GetNotBefore: in 3 occurrence(s), once
  family go:token.Payload.Valid: in 2 occurrence(s), once
  family site:br:184d2ca72d5b: in 2 occurrence(s), once
  family site:br:46e44adad2e4: in 2 occurrence(s), once
  family site:br:8a21855c007e: in 2 occurrence(s), once
  family site:br:b95a526c7153: in 4 occurrence(s), once
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE go:token.Payload.GetExpirationTime  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE go:token.Payload.GetNotBefore  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE site:br:184d2ca72d5b  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE site:br:46e44adad2e4  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.JWTMaker.VerifyToken.<anon>@40 BEFORE site:br:b95a526c7153  (all of the first before all of the second;
      4 occurrence(s), 4 execution(s))
  go:token.Payload.GetExpirationTime BEFORE go:token.Payload.GetNotBefore  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.Payload.GetExpirationTime BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetExpirationTime BEFORE site:br:184d2ca72d5b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:token.Payload.GetExpirationTime BEFORE site:br:46e44adad2e4  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetExpirationTime BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetExpirationTime BEFORE site:br:b95a526c7153  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.Payload.GetNotBefore BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetNotBefore BEFORE site:br:184d2ca72d5b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  go:token.Payload.GetNotBefore BEFORE site:br:46e44adad2e4  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetNotBefore BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  go:token.Payload.GetNotBefore BEFORE site:br:b95a526c7153  (all of the first before all of the second;
      3 occurrence(s), 3 execution(s))
  go:token.Payload.Valid BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:46e44adad2e4 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:46e44adad2e4 BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:b95a526c7153 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:b95a526c7153 BEFORE site:br:184d2ca72d5b  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:b95a526c7153 BEFORE site:br:46e44adad2e4  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))
  site:br:b95a526c7153 BEFORE site:br:8a21855c007e  (all of the first before all of the second;
      2 occurrence(s), 2 execution(s))

inside go:token.PasetoMaker.CreateToken:
  family go:token.NewPayload: in 28 occurrence(s), once
  family site:br:0713394c9923: in 28 occurrence(s), once
  go:token.NewPayload BEFORE site:br:0713394c9923  (all of the first before all of the second;
      28 occurrence(s), 27 execution(s))

inside go:token.PasetoMaker.VerifyToken:
  family go:token.Payload.Valid: in 24 occurrence(s), once
  family site:br:0607e4d952f6: in 24 occurrence(s), once
  family site:br:c7d403dfabc3: in 24 occurrence(s), once
  go:token.Payload.Valid BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      24 occurrence(s), 24 execution(s))
  site:br:0607e4d952f6 BEFORE go:token.Payload.Valid  (all of the first before all of the second;
      24 occurrence(s), 24 execution(s))
  site:br:0607e4d952f6 BEFORE site:br:c7d403dfabc3  (all of the first before all of the second;
      24 occurrence(s), 24 execution(s))

inside go:token.Payload.Valid:
  family site:br:8d10f2f9b136: in 26 occurrence(s), once
  family site:br:bdb0acf90853: in 23 occurrence(s), once
  site:br:8d10f2f9b136 BEFORE site:br:bdb0acf90853  (all of the first before all of the second;
      23 occurrence(s), 23 execution(s))
```

## Mechanics (deterministic, intra-procedural)

### api.Server.createAccount  (api/account.go)
- site br:d82f37a90a3d line 18: `err != nil` | operands: err ← call:ctx.ShouldBindJSON | requires: — | then exits: True, else exits: False
- site br:2edcfe25beec line 31: `err != nil` | operands: err ← call:server.store.CreateAccount#1 | requires: br:d82f37a90a3d=F | then exits: True, else exits: False
- site br:ce254cb89878 line 33: `errCode == db.ForeignKeyViolation || errCode == db.UniqueViolation` | operands: errCode ← call:db.ErrorCode; db.ForeignKeyViolation ← global:db.ForeignKeyViolation; db.UniqueViolation ← global:db.UniqueViolation | requires: br:d82f37a90a3d=F & br:2edcfe25beec=T | then exits: True, else exits: False
- call `ctx.ShouldBindJSON` line 18 requires: —
- call `errorResponse` line 19 requires: br:d82f37a90a3d=T
- call `ctx.JSON` line 19 requires: br:d82f37a90a3d=T
- call `ctx.MustGet` line 23 requires: br:d82f37a90a3d=F
- call `server.store.CreateAccount` line 30 requires: br:d82f37a90a3d=F
- call `db.ErrorCode` line 32 requires: br:d82f37a90a3d=F & br:2edcfe25beec=T
- call `errorResponse` line 34 requires: br:d82f37a90a3d=F & br:2edcfe25beec=T & br:ce254cb89878=T
- call `ctx.JSON` line 34 requires: br:d82f37a90a3d=F & br:2edcfe25beec=T & br:ce254cb89878=T
- call `errorResponse` line 37 requires: br:d82f37a90a3d=F & br:2edcfe25beec=T & br:ce254cb89878=F
- call `ctx.JSON` line 37 requires: br:d82f37a90a3d=F & br:2edcfe25beec=T & br:ce254cb89878=F
- call `ctx.JSON` line 41 requires: br:d82f37a90a3d=F & br:2edcfe25beec=F

### api.Server.getAccount  (api/account.go)
- site br:d8dc32e00682 line 50: `err != nil` | operands: err ← call:ctx.ShouldBindUri | requires: — | then exits: True, else exits: False
- site br:ee83f4152f4f line 56: `err != nil` | operands: err ← call:server.store.GetAccount#1 | requires: br:d8dc32e00682=F | then exits: True, else exits: False
- site br:4831b305602f line 57: `errors.Is(err, db.ErrRecordNotFound)` | operands: errors ← global:errors; err ← call:server.store.GetAccount#1; db.ErrRecordNotFound ← global:db.ErrRecordNotFound | requires: br:d8dc32e00682=F & br:ee83f4152f4f=T | then exits: True, else exits: False
- site br:e5925acb2501 line 67: `account.Owner != authPayload.Username` | operands: account.Owner ← call:server.store.GetAccount#0.Owner; authPayload.Username ← call:ctx.MustGet.Username | requires: br:d8dc32e00682=F & br:ee83f4152f4f=F | then exits: True, else exits: False
- call `ctx.ShouldBindUri` line 50 requires: —
- call `errorResponse` line 51 requires: br:d8dc32e00682=T
- call `ctx.JSON` line 51 requires: br:d8dc32e00682=T
- call `server.store.GetAccount` line 55 requires: br:d8dc32e00682=F
- call `errors.Is` line 57 requires: br:d8dc32e00682=F & br:ee83f4152f4f=T
- call `errorResponse` line 58 requires: br:d8dc32e00682=F & br:ee83f4152f4f=T & br:4831b305602f=T
- call `ctx.JSON` line 58 requires: br:d8dc32e00682=F & br:ee83f4152f4f=T & br:4831b305602f=T
- call `errorResponse` line 62 requires: br:d8dc32e00682=F & br:ee83f4152f4f=T & br:4831b305602f=F
- call `ctx.JSON` line 62 requires: br:d8dc32e00682=F & br:ee83f4152f4f=T & br:4831b305602f=F
- call `ctx.MustGet` line 66 requires: br:d8dc32e00682=F & br:ee83f4152f4f=F
- call `errors.New` line 68 requires: br:d8dc32e00682=F & br:ee83f4152f4f=F & br:e5925acb2501=T
- call `errorResponse` line 69 requires: br:d8dc32e00682=F & br:ee83f4152f4f=F & br:e5925acb2501=T
- call `ctx.JSON` line 69 requires: br:d8dc32e00682=F & br:ee83f4152f4f=F & br:e5925acb2501=T
- call `ctx.JSON` line 73 requires: br:d8dc32e00682=F & br:ee83f4152f4f=F & br:e5925acb2501=F

### api.Server.listAccounts  (api/account.go)
- site br:5264ed92d2dc line 83: `err != nil` | operands: err ← call:ctx.ShouldBindQuery | requires: — | then exits: True, else exits: False
- site br:44fa436929dc line 96: `err != nil` | operands: err ← call:server.store.ListAccounts#1 | requires: br:5264ed92d2dc=F | then exits: True, else exits: False
- call `ctx.ShouldBindQuery` line 83 requires: —
- call `errorResponse` line 84 requires: br:5264ed92d2dc=T
- call `ctx.JSON` line 84 requires: br:5264ed92d2dc=T
- call `ctx.MustGet` line 88 requires: br:5264ed92d2dc=F
- call `server.store.ListAccounts` line 95 requires: br:5264ed92d2dc=F
- call `errorResponse` line 97 requires: br:5264ed92d2dc=F & br:44fa436929dc=T
- call `ctx.JSON` line 97 requires: br:5264ed92d2dc=F & br:44fa436929dc=T
- call `ctx.JSON` line 101 requires: br:5264ed92d2dc=F & br:44fa436929dc=F

### api.errorResponse  (api/server.go)
- call `err.Error` line 66 requires: —

### api.Server.createTransfer  (api/transfer.go)
- site br:896fb396ec78 line 22: `err != nil` | operands: err ← call:ctx.ShouldBindJSON | requires: — | then exits: True, else exits: False
- site br:60a4c43004b3 line 28: `!valid` | operands: valid ← call:server.validAccount#1 | requires: br:896fb396ec78=F | then exits: True, else exits: False
- site br:20ba526fd4ca line 33: `fromAccount.Owner != authPayload.Username` | operands: fromAccount.Owner ← call:server.validAccount#0.Owner; authPayload.Username ← call:ctx.MustGet.Username | requires: br:896fb396ec78=F & br:60a4c43004b3=F | then exits: True, else exits: False
- site br:baf5108f6dd3 line 40: `!valid` | operands: valid ← call:server.validAccount#1 | requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F | then exits: True, else exits: False
- site br:7c52fa3e1b2a line 51: `err != nil` | operands: err ← call:server.store.TransferTx#1 | requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F & br:baf5108f6dd3=F | then exits: True, else exits: False
- call `ctx.ShouldBindJSON` line 22 requires: —
- call `errorResponse` line 23 requires: br:896fb396ec78=T
- call `ctx.JSON` line 23 requires: br:896fb396ec78=T
- call `server.validAccount` line 27 requires: br:896fb396ec78=F
- call `ctx.MustGet` line 32 requires: br:896fb396ec78=F & br:60a4c43004b3=F
- call `errors.New` line 34 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=T
- call `errorResponse` line 35 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=T
- call `ctx.JSON` line 35 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=T
- call `server.validAccount` line 39 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F
- call `server.store.TransferTx` line 50 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F & br:baf5108f6dd3=F
- call `errorResponse` line 52 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F & br:baf5108f6dd3=F & br:7c52fa3e1b2a=T
- call `ctx.JSON` line 52 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F & br:baf5108f6dd3=F & br:7c52fa3e1b2a=T
- call `ctx.JSON` line 56 requires: br:896fb396ec78=F & br:60a4c43004b3=F & br:20ba526fd4ca=F & br:baf5108f6dd3=F & br:7c52fa3e1b2a=F

### api.newUserResponse  (api/user.go)

### api.Server.loginUser  (api/user.go)
- site br:eb7b1a216152 line 90: `err != nil` | operands: err ← call:ctx.ShouldBindJSON | requires: — | then exits: True, else exits: False
- site br:84d886a24efe line 96: `err != nil` | operands: err ← call:server.store.GetUser#1 | requires: br:eb7b1a216152=F | then exits: True, else exits: False
- site br:e540ee8e596a line 97: `errors.Is(err, db.ErrRecordNotFound)` | operands: errors ← global:errors; err ← call:server.store.GetUser#1; db.ErrRecordNotFound ← global:db.ErrRecordNotFound | requires: br:eb7b1a216152=F & br:84d886a24efe=T | then exits: True, else exits: False
- site br:8ac57f80bf1d line 106: `err != nil` | operands: err ← call:util.CheckPassword | requires: br:eb7b1a216152=F & br:84d886a24efe=F | then exits: True, else exits: False
- site br:b2bb97f7167b line 117: `err != nil` | operands: err ← call:server.tokenMaker.CreateToken#2 | requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F | then exits: True, else exits: False
- site br:81d23a5f3d1d line 128: `err != nil` | operands: err ← call:server.tokenMaker.CreateToken#2 | requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F | then exits: True, else exits: False
- site br:7fe5569cfdac line 142: `err != nil` | operands: err ← call:ctx.ClientIP, call:ctx.Request.UserAgent, call:server.store.CreateSession, call:server.store.GetUser#0.Username, call:server.tokenMaker.CreateToken#0, call:server.tokenMaker.CreateToken#1.ExpiredAt, call:server.tokenMaker.CreateToken#1.ID, param:ctx, param:ctx.Request, param:server.store | requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F | then exits: True, else exits: False
- call `ctx.ShouldBindJSON` line 90 requires: —
- call `errorResponse` line 91 requires: br:eb7b1a216152=T
- call `ctx.JSON` line 91 requires: br:eb7b1a216152=T
- call `server.store.GetUser` line 95 requires: br:eb7b1a216152=F
- call `errors.Is` line 97 requires: br:eb7b1a216152=F & br:84d886a24efe=T
- call `errorResponse` line 98 requires: br:eb7b1a216152=F & br:84d886a24efe=T & br:e540ee8e596a=T
- call `ctx.JSON` line 98 requires: br:eb7b1a216152=F & br:84d886a24efe=T & br:e540ee8e596a=T
- call `errorResponse` line 101 requires: br:eb7b1a216152=F & br:84d886a24efe=T & br:e540ee8e596a=F
- call `ctx.JSON` line 101 requires: br:eb7b1a216152=F & br:84d886a24efe=T & br:e540ee8e596a=F
- call `util.CheckPassword` line 105 requires: br:eb7b1a216152=F & br:84d886a24efe=F
- call `errorResponse` line 107 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=T
- call `ctx.JSON` line 107 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=T
- call `server.tokenMaker.CreateToken` line 111 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F
- call `errorResponse` line 118 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=T
- call `ctx.JSON` line 118 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=T
- call `server.tokenMaker.CreateToken` line 122 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F
- call `errorResponse` line 129 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=T
- call `ctx.JSON` line 129 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=T
- call `ctx.Request.UserAgent` line 137 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F
- call `ctx.ClientIP` line 138 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F
- call `server.store.CreateSession` line 133 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F
- call `errorResponse` line 143 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F & br:7fe5569cfdac=T
- call `ctx.JSON` line 143 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F & br:7fe5569cfdac=T
- call `newUserResponse` line 153 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F & br:7fe5569cfdac=F
- call `ctx.JSON` line 155 requires: br:eb7b1a216152=F & br:84d886a24efe=F & br:8ac57f80bf1d=F & br:b2bb97f7167b=F & br:81d23a5f3d1d=F & br:7fe5569cfdac=F

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

### token.Payload.GetExpirationTime  (token/payload.go)

### token.Payload.GetNotBefore  (token/payload.go)

### util.CheckPassword  (util/password.go)
- call `[]byte` line 20 requires: —
- call `[]byte` line 20 requires: —
- call `bcrypt.CompareHashAndPassword` line 20 requires: —

## Observed event logs

Calls of the listed functions in chronological order, indented by depth among them, with argument shapes and value digests, results, exits, and the observed outcome of every decision site evaluated in those calls.

```
### TestAuthMiddleware/ExpiredToken  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#4f1428, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = T
  branch br:c7d403dfabc3 `err != nil` = T
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #a186b5

### TestAuthMiddleware/InvalidAuthorizationFormat  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #f90a84

### TestAuthMiddleware/NoAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #6ea8c1

### TestAuthMiddleware/OK  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#2759bf, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F

### TestAuthMiddleware/UnsupportedAuthorization  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned
call token.PasetoMaker.CreateToken(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7fa7eb, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #6373a5

### TestCreateAccountAPI/InternalError  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#bb34c1, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.createAccount(ctx=*gin.Context) [returned]
  branch br:d82f37a90a3d `err != nil` = F
  branch br:2edcfe25beec `err != nil` = T
  branch br:ce254cb89878 `errCode == db.ForeignKeyViolation || errCode == db.UniqueViolation` = F
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #797549

### TestCreateAccountAPI/InvalidCurrency  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#bda7b8, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.createAccount(ctx=*gin.Context) [returned]
  branch br:d82f37a90a3d `err != nil` = T
  call api.errorResponse(err=validator.ValidationErrors[1]) [returned] -> #28773c

### TestCreateAccountAPI/NoAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #6ea8c1

### TestCreateAccountAPI/OK  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#822ca9, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#ffb507, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.createAccount(ctx=*gin.Context) [returned]
  branch br:d82f37a90a3d `err != nil` = F
  branch br:2edcfe25beec `err != nil` = F

### TestExpiredJWTToken  test: passed  exits: token.JWTMaker.CreateToken returned; token.NewPayload returned; token.JWTMaker.VerifyToken returned-error:go:*errors.errorString
call token.JWTMaker.CreateToken(username=string#a6ec52, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#a6ec52, role=string#2ab61d, duration=time.Duration#6efa86, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:d9f1e0c214f9 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#047a72, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  call token.JWTMaker.VerifyToken.<anon>@40(token=*jwt.Token) [returned]
    branch br:47a837559e89 `?` = F
  call token.Payload.GetExpirationTime() [returned]
  call token.Payload.GetNotBefore() [returned]
  branch br:b95a526c7153 `err != nil` = T
  branch br:184d2ca72d5b `errors.Is(err, jwt.ErrTokenExpired)` = T

### TestExpiredPasetoToken  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
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

### TestGetAccountAPI/InternalError  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#ac23c9, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.getAccount(ctx=*gin.Context) [returned]
  branch br:d8dc32e00682 `err != nil` = F
  branch br:ee83f4152f4f `err != nil` = T
  branch br:4831b305602f `errors.Is(err, db.ErrRecordNotFound)` = F
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #797549

### TestGetAccountAPI/InvalidID  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#2eb6f0, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.getAccount(ctx=*gin.Context) [returned]
  branch br:d8dc32e00682 `err != nil` = T
  call api.errorResponse(err=validator.ValidationErrors[1]) [returned] -> #a7a431

### TestGetAccountAPI/NoAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #6ea8c1

### TestGetAccountAPI/NotFound  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#73a87b, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.getAccount(ctx=*gin.Context) [returned]
  branch br:d8dc32e00682 `err != nil` = F
  branch br:ee83f4152f4f `err != nil` = T
  branch br:4831b305602f `errors.Is(err, db.ErrRecordNotFound)` = T
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #798485

### TestGetAccountAPI/OK  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#0ff281, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#f13967, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.getAccount(ctx=*gin.Context) [returned]
  branch br:d8dc32e00682 `err != nil` = F
  branch br:ee83f4152f4f `err != nil` = F
  branch br:e5925acb2501 `account.Owner != authPayload.Username` = F

### TestGetAccountAPI/UnauthorizedUser  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#b382a1, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#b382a1, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#5d7b6c, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.getAccount(ctx=*gin.Context) [returned]
  branch br:d8dc32e00682 `err != nil` = F
  branch br:ee83f4152f4f `err != nil` = F
  branch br:e5925acb2501 `account.Owner != authPayload.Username` = T
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #c79832

### TestInvalidJWTTokenAlgNone  test: passed  exits: token.NewPayload returned; token.JWTMaker.VerifyToken returned-error:go:*errors.errorString
call token.NewPayload(username=string#f1c5f1, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  branch br:ecd8b89da8b7 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#f4f56a, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
  call token.JWTMaker.VerifyToken.<anon>@40(token=*jwt.Token) [returned-error:go:*errors.errorString]
    branch br:47a837559e89 `?` = T
  branch br:b95a526c7153 `err != nil` = T
  branch br:184d2ca72d5b `errors.Is(err, jwt.ErrTokenExpired)` = F

### TestJWTMaker  test: passed  exits: token.JWTMaker.CreateToken returned; token.NewPayload returned; token.JWTMaker.VerifyToken returned; token.Payload.Valid returned
call token.JWTMaker.CreateToken(username=string#5d3dd3, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5d3dd3, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:d9f1e0c214f9 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#d21de1, tokenType=token.TokenType#35ddf6) [returned]
  call token.JWTMaker.VerifyToken.<anon>@40(token=*jwt.Token) [returned]
    branch br:47a837559e89 `?` = F
  call token.Payload.GetExpirationTime() [returned]
  call token.Payload.GetNotBefore() [returned]
  branch br:b95a526c7153 `err != nil` = F
  branch br:46e44adad2e4 `!ok` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:8a21855c007e `err != nil` = F

### TestJWTWrongTokenType  test: passed  exits: token.JWTMaker.CreateToken returned; token.NewPayload returned; token.JWTMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
call token.JWTMaker.CreateToken(username=string#e78091, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#e78091, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:d9f1e0c214f9 `err != nil` = F
call token.JWTMaker.VerifyToken(token=string#c085d6, tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
  call token.JWTMaker.VerifyToken.<anon>@40(token=*jwt.Token) [returned]
    branch br:47a837559e89 `?` = F
  call token.Payload.GetExpirationTime() [returned]
  call token.Payload.GetNotBefore() [returned]
  branch br:b95a526c7153 `err != nil` = F
  branch br:46e44adad2e4 `!ok` = F
  call token.Payload.Valid(tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
    branch br:8d10f2f9b136 `payload.Type != tokenType` = T
  branch br:8a21855c007e `err != nil` = T

### TestListAccountsAPI/InternalError  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#6a0461, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.listAccounts(ctx=*gin.Context) [returned]
  branch br:5264ed92d2dc `err != nil` = F
  branch br:44fa436929dc `err != nil` = T
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #797549

### TestListAccountsAPI/InvalidPageID  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#e9c55d, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.listAccounts(ctx=*gin.Context) [returned]
  branch br:5264ed92d2dc `err != nil` = T
  call api.errorResponse(err=validator.ValidationErrors[1]) [returned] -> #9ae9cc

### TestListAccountsAPI/InvalidPageSize  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#a2bdbb, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.listAccounts(ctx=*gin.Context) [returned]
  branch br:5264ed92d2dc `err != nil` = T
  call api.errorResponse(err=validator.ValidationErrors[1]) [returned] -> #c8f7a5

### TestListAccountsAPI/NoAuthorization  test: passed  exits: api.authMiddleware.<anon>@21 returned
call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #6ea8c1

### TestListAccountsAPI/OK  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#5bbdfd, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#3dd6d4, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.listAccounts(ctx=*gin.Context) [returned]
  branch br:5264ed92d2dc `err != nil` = F
  branch br:44fa436929dc `err != nil` = F

### TestLoginUserAPI/IncorrectPassword  test: passed  exits: api.Server.loginUser returned
call api.Server.loginUser(ctx=*gin.Context) [returned]
  branch br:eb7b1a216152 `err != nil` = F
  branch br:84d886a24efe `err != nil` = F
  call util.CheckPassword(password=string#ce8c2a, hashedPassword=string#c3f3d7) [returned-error:go:*errors.errorString]
  branch br:8ac57f80bf1d `err != nil` = T
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #a8af6e

### TestLoginUserAPI/InternalError  test: passed  exits: api.Server.loginUser returned
call api.Server.loginUser(ctx=*gin.Context) [returned]
  branch br:eb7b1a216152 `err != nil` = F
  branch br:84d886a24efe `err != nil` = T
  branch br:e540ee8e596a `errors.Is(err, db.ErrRecordNotFound)` = F
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #797549

### TestLoginUserAPI/InvalidUsername  test: passed  exits: api.Server.loginUser returned
call api.Server.loginUser(ctx=*gin.Context) [returned]
  branch br:eb7b1a216152 `err != nil` = T
  call api.errorResponse(err=validator.ValidationErrors[1]) [returned] -> #0858b5

### TestLoginUserAPI/OK  test: passed  exits: api.Server.loginUser returned; token.PasetoMaker.CreateToken returned; token.NewPayload returned; token.PasetoMaker.CreateToken returned; token.NewPayload returned
call api.Server.loginUser(ctx=*gin.Context) [returned]
  branch br:eb7b1a216152 `err != nil` = F
  branch br:84d886a24efe `err != nil` = F
  call util.CheckPassword(password=string#a90a1e, hashedPassword=string#c3f3d7) [returned] -> #5da3a4
  branch br:8ac57f80bf1d `err != nil` = F
  call token.PasetoMaker.CreateToken(username=string#024456, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    call token.NewPayload(username=string#024456, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
      branch br:ecd8b89da8b7 `err != nil` = F
    branch br:0713394c9923 `err != nil` = F
  branch br:b2bb97f7167b `err != nil` = F
  call token.PasetoMaker.CreateToken(username=string#024456, role=string#e087fa, duration=time.Duration#513b14, tokenType=token.TokenType#018508) [returned]
    call token.NewPayload(username=string#024456, role=string#e087fa, duration=time.Duration#513b14, tokenType=token.TokenType#018508) [returned]
      branch br:ecd8b89da8b7 `err != nil` = F
    branch br:0713394c9923 `err != nil` = F
  branch br:81d23a5f3d1d `err != nil` = F
  branch br:7fe5569cfdac `err != nil` = F
  call api.newUserResponse(user=db.User#cd62ca) [returned] -> #701ba1

### TestLoginUserAPI/UserNotFound  test: passed  exits: api.Server.loginUser returned
call api.Server.loginUser(ctx=*gin.Context) [returned]
  branch br:eb7b1a216152 `err != nil` = F
  branch br:84d886a24efe `err != nil` = T
  branch br:e540ee8e596a `errors.Is(err, db.ErrRecordNotFound)` = T
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #798485

### TestPasetoMaker  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
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

### TestPasetoWrongTokenType  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#982f5e, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#982f5e, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#614b02, tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#018508) [returned-error:go:*errors.errorString]
    branch br:8d10f2f9b136 `payload.Type != tokenType` = T
  branch br:c7d403dfabc3 `err != nil` = T

### TestTransferAPI/FromAccountCurrencyMismatch  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#c9a6c2, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#c9a6c2, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#38854f, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.createTransfer(ctx=*gin.Context) [returned]
  branch br:896fb396ec78 `err != nil` = F
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #93b737
  branch br:60a4c43004b3 `!valid` = T

### TestTransferAPI/FromAccountNotFound  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; api.authMiddleware.<anon>@21 returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
call token.PasetoMaker.CreateToken(username=string#7be6ea, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
  call token.NewPayload(username=string#7be6ea, role=string#e087fa, duration=time.Duration#f5e4f3, tokenType=token.TokenType#35ddf6) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call token.PasetoMaker.VerifyToken(token=string#b16ede, tokenType=token.TokenType#35ddf6) [returned]
  branch br:0607e4d952f6 `err != nil` = F
  call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned] -> #5da3a4
    branch br:8d10f2f9b136 `payload.Type != tokenType` = F
    branch br:bdb0acf90853 `time.Now().After(payload.ExpiredAt)` = F
  branch br:c7d403dfabc3 `err != nil` = F
call api.Server.createTransfer(ctx=*gin.Context) [returned]
  branch br:896fb396ec78 `err != nil` = F
  call api.errorResponse(err=*errors.errorString#e35f8d) [returned] -> #798485
  branch br:60a4c43004b3 `!valid` = T

### TestUpdateUserAPI/BankerCanUpdateUserInfo  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.authorizeUser returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
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
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = F
  branch br:815be3bfb43a `req.Password != nil` = F
  branch br:17f2bce25a0f `err != nil` = F

### TestUpdateUserAPI/ExpiredToken  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.authorizeUser returned-error:go:*errors.errorString; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
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

### TestUpdateUserAPI/InvalidEmail  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.authorizeUser returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
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
  branch br:af0e24f4367b `violations != nil` = T

### TestUpdateUserAPI/NoAuthorization  test: passed  exits: gapi.Server.authorizeUser returned-error:go:*errors.errorString
call gapi.Server.UpdateUser(ctx=context.backgroundCtx#2e2a50, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=context.backgroundCtx#2e2a50, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = T
  branch br:0746154f1c47 `err != nil` = T

### TestUpdateUserAPI/OtherDepositorCannotUpdateThisUserInfo  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.authorizeUser returned; token.PasetoMaker.VerifyToken returned; token.Payload.Valid returned
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
  branch br:af0e24f4367b `violations != nil` = F
  branch br:01807a7b80a2 `authPayload.Role != util.BankerRole && authPayload.Username != req.Get` = T

### TestUpdateUserAPI/WrongTokenType  test: passed  exits: token.PasetoMaker.CreateToken returned; token.NewPayload returned; gapi.Server.authorizeUser returned-error:go:*errors.errorString; token.PasetoMaker.VerifyToken returned-error:go:*errors.errorString; token.Payload.Valid returned-error:go:*errors.errorString
call token.PasetoMaker.CreateToken(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#018508) [returned]
  call token.NewPayload(username=string#c720df, role=string#2ab61d, duration=time.Duration#f5e4f3, tokenType=token.TokenType#018508) [returned]
    branch br:ecd8b89da8b7 `err != nil` = F
  branch br:0713394c9923 `err != nil` = F
call gapi.Server.UpdateUser(ctx=*context.valueCtx, req=*pb.UpdateUserRequest#914e8d) [returned-error:go:*status.Error]
  call gapi.Server.authorizeUser(ctx=*context.valueCtx, accessibleRoles=[]string[2]#0bd72d) [returned-error:go:*errors.errorString]
    branch br:e3505bc4c4b9 `!ok` = F
    branch br:a572eeb6a4c8 `len(values) == 0` = F
    branch br:4393757b65d7 `len(fields) < 2` = F
    branch br:2e2f712d6301 `authType != authorizationBearer` = F
    call token.PasetoMaker.VerifyToken(token=string#8d9b66, tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
      branch br:0607e4d952f6 `err != nil` = F
      call token.Payload.Valid(tokenType=token.TokenType#35ddf6) [returned-error:go:*errors.errorString]
        branch br:8d10f2f9b136 `payload.Type != tokenType` = T
      branch br:c7d403dfabc3 `err != nil` = T
    branch br:c71158777bce `err != nil` = T
  branch br:0746154f1c47 `err != nil` = T
```

## The change (git diff 7c6f92f2bc5dd7ffe30552bd2fe9699de06b5512..97f000fe58ad01a0774179ffa8884ac7784cf263, the files shown below)

```diff
diff --git a/api/middleware.go b/api/middleware.go
index dfd5525..56b5ddd 100644
--- a/api/middleware.go
+++ b/api/middleware.go
@@ -20,35 +20,35 @@ const (
 func authMiddleware(tokenMaker token.Maker) gin.HandlerFunc {
 	return func(ctx *gin.Context) {
 		authorizationHeader := ctx.GetHeader(authorizationHeaderKey)
 
 		if len(authorizationHeader) == 0 {
 			err := errors.New("authorization header is not provided")
 			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
 			return
 		}
 
 		fields := strings.Fields(authorizationHeader)
 		if len(fields) < 2 {
 			err := errors.New("invalid authorization header format")
 			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
 			return
 		}
 
 		authorizationType := strings.ToLower(fields[0])
 		if authorizationType != authorizationTypeBearer {
 			err := fmt.Errorf("unsupported authorization type %s", authorizationType)
 			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
 			return
 		}
 
 		accessToken := fields[1]
-		payload, err := tokenMaker.VerifyToken(accessToken)
+		payload, err := tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
 		if err != nil {
 			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
 			return
 		}
 
 		ctx.Set(authorizationPayloadKey, payload)
 		ctx.Next()
 	}
 }
diff --git a/api/token.go b/api/token.go
index 7d7b615..7183ad7 100644
--- a/api/token.go
+++ b/api/token.go
@@ -1,84 +1,86 @@
 package api
 
 import (
 	"errors"
 	"fmt"
 	"net/http"
 	"time"
 
 	"github.com/gin-gonic/gin"
 	db "github.com/techschool/simplebank/db/sqlc"
+	"github.com/techschool/simplebank/token"
 )
 
 type renewAccessTokenRequest struct {
 	RefreshToken string `json:"refresh_token" binding:"required"`
 }
 
 type renewAccessTokenResponse struct {
 	AccessToken          string    `json:"access_token"`
 	AccessTokenExpiresAt time.Time `json:"access_token_expires_at"`
 }
 
 func (server *Server) renewAccessToken(ctx *gin.Context) {
 	var req renewAccessTokenRequest
 	if err := ctx.ShouldBindJSON(&req); err != nil {
 		ctx.JSON(http.StatusBadRequest, errorResponse(err))
 		return
 	}
 
-	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken)
+	refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken, token.TokenTypeRefreshToken)
 	if err != nil {
 		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 		return
 	}
 
 	session, err := server.store.GetSession(ctx, refreshPayload.ID)
 	if err != nil {
 		if errors.Is(err, db.ErrRecordNotFound) {
 			ctx.JSON(http.StatusNotFound, errorResponse(err))
 			return
 		}
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	if session.IsBlocked {
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
 		refreshPayload.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
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
index 94de476..640f3c6 100644
--- a/api/user.go
+++ b/api/user.go
@@ -1,35 +1,36 @@
 package api
 
 import (
 	"errors"
 	"net/http"
 	"time"
 
 	"github.com/gin-gonic/gin"
 	"github.com/google/uuid"
 	db "github.com/techschool/simplebank/db/sqlc"
+	"github.com/techschool/simplebank/token"
 	"github.com/techschool/simplebank/util"
 )
 
 type createUserRequest struct {
 	Username string `json:"username" binding:"required,alphanum"`
 	Password string `json:"password" binding:"required,min=6"`
 	FullName string `json:"full_name" binding:"required"`
 	Email    string `json:"email" binding:"required,email"`
 }
 
 type userResponse struct {
 	Username          string    `json:"username"`
 	FullName          string    `json:"full_name"`
 	Email             string    `json:"email"`
 	PasswordChangedAt time.Time `json:"password_changed_at"`
 	CreatedAt         time.Time `json:"created_at"`
 }
 
 func newUserResponse(user db.User) userResponse {
 	return userResponse{
 		Username:          user.Username,
 		FullName:          user.FullName,
 		Email:             user.Email,
 		PasswordChangedAt: user.PasswordChangedAt,
 		CreatedAt:         user.CreatedAt,
@@ -89,60 +90,62 @@ func (server *Server) loginUser(ctx *gin.Context) {
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
 		user.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
 	)
 	if err != nil {
 		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 		return
 	}
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
 		user.Role,
 		server.config.RefreshTokenDuration,
+		token.TokenTypeRefreshToken,
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
 		RefreshToken:          refreshToken,
diff --git a/gapi/authorization.go b/gapi/authorization.go
index 892467d..3c76d66 100644
--- a/gapi/authorization.go
+++ b/gapi/authorization.go
@@ -15,45 +15,45 @@ const (
 )
 
 func (server *Server) authorizeUser(ctx context.Context, accessibleRoles []string) (*token.Payload, error) {
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
-	payload, err := server.tokenMaker.VerifyToken(accessToken)
+	payload, err := server.tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
 	if err != nil {
 		return nil, fmt.Errorf("invalid access token: %s", err)
 	}
 
 	if !hasPermission(payload.Role, accessibleRoles) {
 		return nil, fmt.Errorf("permission denied")
 	}
 
 	return payload, nil
 }
 
 func hasPermission(userRole string, accessibleRoles []string) bool {
 	for _, role := range accessibleRoles {
 		if userRole == role {
 			return true
 		}
 	}
 	return false
 }
diff --git a/gapi/rpc_create_user.go b/gapi/rpc_create_user.go
index ec87dd0..66b2ee6 100644
--- a/gapi/rpc_create_user.go
+++ b/gapi/rpc_create_user.go
@@ -28,51 +28,51 @@ func (server *Server) CreateUser(ctx context.Context, req *pb.CreateUserRequest)
 
 	arg := db.CreateUserTxParams{
 		CreateUserParams: db.CreateUserParams{
 			Username:       req.GetUsername(),
 			HashedPassword: hashedPassword,
 			FullName:       req.GetFullName(),
 			Email:          req.GetEmail(),
 		},
 		AfterCreate: func(user db.User) error {
 			taskPayload := &worker.PayloadSendVerifyEmail{
 				Username: user.Username,
 			}
 			opts := []asynq.Option{
 				asynq.MaxRetry(10),
 				asynq.ProcessIn(10 * time.Second),
 				asynq.Queue(worker.QueueCritical),
 			}
 
 			return server.taskDistributor.DistributeTaskSendVerifyEmail(ctx, taskPayload, opts...)
 		},
 	}
 
 	txResult, err := server.store.CreateUserTx(ctx, arg)
 	if err != nil {
 		if db.ErrorCode(err) == db.UniqueViolation {
-			return nil, status.Errorf(codes.AlreadyExists, err.Error())
+			return nil, status.Error(codes.AlreadyExists, err.Error())
 		}
 		return nil, status.Errorf(codes.Internal, "failed to create user: %s", err)
 	}
 
 	rsp := &pb.CreateUserResponse{
 		User: convertUser(txResult.User),
 	}
 	return rsp, nil
 }
 
 func validateCreateUserRequest(req *pb.CreateUserRequest) (violations []*errdetails.BadRequest_FieldViolation) {
 	if err := val.ValidateUsername(req.GetUsername()); err != nil {
 		violations = append(violations, fieldViolation("username", err))
 	}
 
 	if err := val.ValidatePassword(req.GetPassword()); err != nil {
 		violations = append(violations, fieldViolation("password", err))
 	}
 
 	if err := val.ValidateFullName(req.GetFullName()); err != nil {
 		violations = append(violations, fieldViolation("full_name", err))
 	}
 
 	if err := val.ValidateEmail(req.GetEmail()); err != nil {
 		violations = append(violations, fieldViolation("email", err))
diff --git a/gapi/rpc_login_user.go b/gapi/rpc_login_user.go
index 259ba21..139a953 100644
--- a/gapi/rpc_login_user.go
+++ b/gapi/rpc_login_user.go
@@ -1,73 +1,76 @@
 package gapi
 
 import (
 	"context"
 	"errors"
 
 	db "github.com/techschool/simplebank/db/sqlc"
 	"github.com/techschool/simplebank/pb"
+	"github.com/techschool/simplebank/token"
 	"github.com/techschool/simplebank/util"
 	"github.com/techschool/simplebank/val"
 	"google.golang.org/genproto/googleapis/rpc/errdetails"
 	"google.golang.org/grpc/codes"
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
 		user.Role,
 		server.config.AccessTokenDuration,
+		token.TokenTypeAccessToken,
 	)
 	if err != nil {
 		return nil, status.Errorf(codes.Internal, "failed to create access token")
 	}
 
 	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 		user.Username,
 		user.Role,
 		server.config.RefreshTokenDuration,
+		token.TokenTypeRefreshToken,
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
 		AccessTokenExpiresAt:  timestamppb.New(accessPayload.ExpiredAt),
diff --git a/token/jwt_maker.go b/token/jwt_maker.go
index c130dfa..59af469 100644
--- a/token/jwt_maker.go
+++ b/token/jwt_maker.go
@@ -2,61 +2,66 @@ package token
 
 import (
 	"errors"
 	"fmt"
 	"time"
 
 	"github.com/golang-jwt/jwt/v5"
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
-func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, role, duration)
+func (maker *JWTMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration, tokenType)
 	if err != nil {
 		return "", payload, err
 	}
 
 	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, payload)
 	token, err := jwtToken.SignedString([]byte(maker.secretKey))
 	return token, payload, err
 }
 
 // VerifyToken checks if the token is valid or not
-func (maker *JWTMaker) VerifyToken(token string) (*Payload, error) {
+func (maker *JWTMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
 	keyFunc := func(token *jwt.Token) (interface{}, error) {
 		_, ok := token.Method.(*jwt.SigningMethodHMAC)
 		if !ok {
 			return nil, ErrInvalidToken
 		}
 		return []byte(maker.secretKey), nil
 	}
 
 	jwtToken, err := jwt.ParseWithClaims(token, &Payload{}, keyFunc)
 	if err != nil {
 		if errors.Is(err, jwt.ErrTokenExpired) {
 			return nil, ErrExpiredToken
 		}
 		return nil, ErrInvalidToken
 	}
 
 	payload, ok := jwtToken.Claims.(*Payload)
 	if !ok {
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
@@ -1,14 +1,14 @@
 package token
 
 import (
 	"time"
 )
 
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
-func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration) (string, *Payload, error) {
-	payload, err := NewPayload(username, role, duration)
+func (maker *PasetoMaker) CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error) {
+	payload, err := NewPayload(username, role, duration, tokenType)
 	if err != nil {
 		return "", payload, err
 	}
 
 	token, err := maker.paseto.Encrypt(maker.symmetricKey, payload, nil)
 	return token, payload, err
 }
 
 // VerifyToken checks if the token is valid or not
-func (maker *PasetoMaker) VerifyToken(token string) (*Payload, error) {
+func (maker *PasetoMaker) VerifyToken(token string, tokenType TokenType) (*Payload, error) {
 	payload := &Payload{}
 
 	err := maker.paseto.Decrypt(token, maker.symmetricKey, payload, nil)
 	if err != nil {
 		return nil, ErrInvalidToken
 	}
 
-	err = payload.Valid()
+	err = payload.Valid(tokenType)
 	if err != nil {
 		return nil, err
 	}
 
 	return payload, nil
 }
diff --git a/token/payload.go b/token/payload.go
index 05ec639..2130681 100644
--- a/token/payload.go
+++ b/token/payload.go
@@ -1,69 +1,81 @@
 package token
 
 import (
 	"errors"
 	"time"
 
 	"github.com/golang-jwt/jwt/v5"
 	"github.com/google/uuid"
 )
 
 // Different types of error returned by the VerifyToken function
 var (
 	ErrInvalidToken = errors.New("token is invalid")
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
 	ExpiredAt time.Time `json:"expired_at"`
 }
 
 // NewPayload creates a new token payload with a specific username and duration
-func NewPayload(username string, role string, duration time.Duration) (*Payload, error) {
+func NewPayload(username string, role string, duration time.Duration, tokenType TokenType) (*Payload, error) {
 	tokenID, err := uuid.NewRandom()
 	if err != nil {
 		return nil, err
 	}
 
 	payload := &Payload{
 		ID:        tokenID,
+		Type:      tokenType,
 		Username:  username,
 		Role:      role,
 		IssuedAt:  time.Now(),
 		ExpiredAt: time.Now().Add(duration),
 	}
 	return payload, nil
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
 	return nil
 }
 
 func (payload *Payload) GetExpirationTime() (*jwt.NumericDate, error) {
 	return &jwt.NumericDate{
 		Time: payload.ExpiredAt,
 	}, nil
 }
 
 func (payload *Payload) GetIssuedAt() (*jwt.NumericDate, error) {
 	return &jwt.NumericDate{
 		Time: payload.IssuedAt,
 	}, nil
 }
 
 func (payload *Payload) GetNotBefore() (*jwt.NumericDate, error) {
 	return &jwt.NumericDate{
 		Time: payload.IssuedAt,
 	}, nil
 }
 
 func (payload *Payload) GetIssuer() (string, error) {
```

## Source: api/account.go

```
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"net/http"
   6  
   7  	"github.com/gin-gonic/gin"
   8  	db "github.com/techschool/simplebank/db/sqlc"
   9  	"github.com/techschool/simplebank/token"
  10  )
  11  
  12  type createAccountRequest struct {
  13  	Currency string `json:"currency" binding:"required,currency"`
  14  }
  15  
  16  func (server *Server) createAccount(ctx *gin.Context) {
  17  	var req createAccountRequest
  18  	if err := ctx.ShouldBindJSON(&req); err != nil {
  19  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  20  		return
  21  	}
  22  
  23  	authPayload := ctx.MustGet(authorizationPayloadKey).(*token.Payload)
  24  	arg := db.CreateAccountParams{
  25  		Owner:    authPayload.Username,
  26  		Currency: req.Currency,
  27  		Balance:  0,
  28  	}
  29  
  30  	account, err := server.store.CreateAccount(ctx, arg)
  31  	if err != nil {
  32  		errCode := db.ErrorCode(err)
  33  		if errCode == db.ForeignKeyViolation || errCode == db.UniqueViolation {
  34  			ctx.JSON(http.StatusForbidden, errorResponse(err))
  35  			return
  36  		}
  37  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  38  		return
  39  	}
  40  
  41  	ctx.JSON(http.StatusOK, account)
  42  }
  43  
  44  type getAccountRequest struct {
  45  	ID int64 `uri:"id" binding:"required,min=1"`
  46  }
  47  
  48  func (server *Server) getAccount(ctx *gin.Context) {
  49  	var req getAccountRequest
  50  	if err := ctx.ShouldBindUri(&req); err != nil {
  51  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  52  		return
  53  	}
  54  
  55  	account, err := server.store.GetAccount(ctx, req.ID)
  56  	if err != nil {
  57  		if errors.Is(err, db.ErrRecordNotFound) {
  58  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  59  			return
  60  		}
  61  
  62  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  63  		return
  64  	}
  65  
  66  	authPayload := ctx.MustGet(authorizationPayloadKey).(*token.Payload)
  67  	if account.Owner != authPayload.Username {
  68  		err := errors.New("account doesn't belong to the authenticated user")
  69  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  70  		return
  71  	}
  72  
  73  	ctx.JSON(http.StatusOK, account)
  74  }
  75  
  76  type listAccountRequest struct {
  77  	PageID   int32 `form:"page_id" binding:"required,min=1"`
  78  	PageSize int32 `form:"page_size" binding:"required,min=5,max=10"`
  79  }
  80  
  81  func (server *Server) listAccounts(ctx *gin.Context) {
  82  	var req listAccountRequest
  83  	if err := ctx.ShouldBindQuery(&req); err != nil {
  84  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  85  		return
  86  	}
  87  
  88  	authPayload := ctx.MustGet(authorizationPayloadKey).(*token.Payload)
  89  	arg := db.ListAccountsParams{
  90  		Owner:  authPayload.Username,
  91  		Limit:  req.PageSize,
  92  		Offset: (req.PageID - 1) * req.PageSize,
  93  	}
  94  
  95  	accounts, err := server.store.ListAccounts(ctx, arg)
  96  	if err != nil {
  97  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  98  		return
  99  	}
 100  
 101  	ctx.JSON(http.StatusOK, accounts)
 102  }
```

## Source: api/server.go

```
   1  package api
   2  
   3  import (
   4  	"fmt"
   5  
   6  	"github.com/gin-gonic/gin"
   7  	"github.com/gin-gonic/gin/binding"
   8  	"github.com/go-playground/validator/v10"
   9  	db "github.com/techschool/simplebank/db/sqlc"
  10  	"github.com/techschool/simplebank/token"
  11  	"github.com/techschool/simplebank/util"
  12  )
  13  
  14  // Server serves HTTP requests for our banking service.
  15  type Server struct {
  16  	config     util.Config
  17  	store      db.Store
  18  	tokenMaker token.Maker
  19  	router     *gin.Engine
  20  }
  21  
  22  // NewServer creates a new HTTP server and set up routing.
  23  func NewServer(config util.Config, store db.Store) (*Server, error) {
  24  	tokenMaker, err := token.NewPasetoMaker(config.TokenSymmetricKey)
  25  	if err != nil {
  26  		return nil, fmt.Errorf("cannot create token maker: %w", err)
  27  	}
  28  
  29  	server := &Server{
  30  		config:     config,
  31  		store:      store,
  32  		tokenMaker: tokenMaker,
  33  	}
  34  
  35  	if v, ok := binding.Validator.Engine().(*validator.Validate); ok {
  36  		v.RegisterValidation("currency", validCurrency)
  37  	}
  38  
  39  	server.setupRouter()
  40  	return server, nil
  41  }
  42  
  43  func (server *Server) setupRouter() {
  44  	router := gin.Default()
  45  
  46  	router.POST("/users", server.createUser)
  47  	router.POST("/users/login", server.loginUser)
  48  	router.POST("/tokens/renew_access", server.renewAccessToken)
  49  
  50  	authRoutes := router.Group("/").Use(authMiddleware(server.tokenMaker))
  51  	authRoutes.POST("/accounts", server.createAccount)
  52  	authRoutes.GET("/accounts/:id", server.getAccount)
  53  	authRoutes.GET("/accounts", server.listAccounts)
  54  
  55  	authRoutes.POST("/transfers", server.createTransfer)
  56  
  57  	server.router = router
  58  }
  59  
  60  // Start runs the HTTP server on a specific address.
  61  func (server *Server) Start(address string) error {
  62  	return server.router.Run(address)
  63  }
  64  
  65  func errorResponse(err error) gin.H {
  66  	return gin.H{"error": err.Error()}
  67  }
```

## Source: api/transfer.go

```
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"net/http"
   7  
   8  	"github.com/gin-gonic/gin"
   9  	db "github.com/techschool/simplebank/db/sqlc"
  10  	"github.com/techschool/simplebank/token"
  11  )
  12  
  13  type transferRequest struct {
  14  	FromAccountID int64  `json:"from_account_id" binding:"required,min=1"`
  15  	ToAccountID   int64  `json:"to_account_id" binding:"required,min=1"`
  16  	Amount        int64  `json:"amount" binding:"required,gt=0"`
  17  	Currency      string `json:"currency" binding:"required,currency"`
  18  }
  19  
  20  func (server *Server) createTransfer(ctx *gin.Context) {
  21  	var req transferRequest
  22  	if err := ctx.ShouldBindJSON(&req); err != nil {
  23  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  24  		return
  25  	}
  26  
  27  	fromAccount, valid := server.validAccount(ctx, req.FromAccountID, req.Currency)
  28  	if !valid {
  29  		return
  30  	}
  31  
  32  	authPayload := ctx.MustGet(authorizationPayloadKey).(*token.Payload)
  33  	if fromAccount.Owner != authPayload.Username {
  34  		err := errors.New("from account doesn't belong to the authenticated user")
  35  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  36  		return
  37  	}
  38  
  39  	_, valid = server.validAccount(ctx, req.ToAccountID, req.Currency)
  40  	if !valid {
  41  		return
  42  	}
  43  
  44  	arg := db.TransferTxParams{
  45  		FromAccountID: req.FromAccountID,
  46  		ToAccountID:   req.ToAccountID,
  47  		Amount:        req.Amount,
  48  	}
  49  
  50  	result, err := server.store.TransferTx(ctx, arg)
  51  	if err != nil {
  52  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  53  		return
  54  	}
  55  
  56  	ctx.JSON(http.StatusOK, result)
  57  }
  58  
  59  func (server *Server) validAccount(ctx *gin.Context, accountID int64, currency string) (db.Account, bool) {
  60  	account, err := server.store.GetAccount(ctx, accountID)
  61  	if err != nil {
  62  		if errors.Is(err, db.ErrRecordNotFound) {
  63  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  64  			return account, false
  65  		}
  66  
  67  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  68  		return account, false
  69  	}
  70  
  71  	if account.Currency != currency {
  72  		err := fmt.Errorf("account [%d] currency mismatch: %s vs %s", account.ID, account.Currency, currency)
  73  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  74  		return account, false
  75  	}
  76  
  77  	return account, true
  78  }
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
  11  	"github.com/techschool/simplebank/token"
  12  	"github.com/techschool/simplebank/util"
  13  )
  14  
  15  type createUserRequest struct {
  16  	Username string `json:"username" binding:"required,alphanum"`
  17  	Password string `json:"password" binding:"required,min=6"`
  18  	FullName string `json:"full_name" binding:"required"`
  19  	Email    string `json:"email" binding:"required,email"`
  20  }
  21  
  22  type userResponse struct {
  23  	Username          string    `json:"username"`
  24  	FullName          string    `json:"full_name"`
  25  	Email             string    `json:"email"`
  26  	PasswordChangedAt time.Time `json:"password_changed_at"`
  27  	CreatedAt         time.Time `json:"created_at"`
  28  }
  29  
  30  func newUserResponse(user db.User) userResponse {
  31  	return userResponse{
  32  		Username:          user.Username,
  33  		FullName:          user.FullName,
  34  		Email:             user.Email,
  35  		PasswordChangedAt: user.PasswordChangedAt,
  36  		CreatedAt:         user.CreatedAt,
  37  	}
  38  }
  39  
  40  func (server *Server) createUser(ctx *gin.Context) {
  41  	var req createUserRequest
  42  	if err := ctx.ShouldBindJSON(&req); err != nil {
  43  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  44  		return
  45  	}
  46  
  47  	hashedPassword, err := util.HashPassword(req.Password)
  48  	if err != nil {
  49  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  50  		return
  51  	}
  52  
  53  	arg := db.CreateUserParams{
  54  		Username:       req.Username,
  55  		HashedPassword: hashedPassword,
  56  		FullName:       req.FullName,
  57  		Email:          req.Email,
  58  	}
  59  
  60  	user, err := server.store.CreateUser(ctx, arg)
  61  	if err != nil {
  62  		if db.ErrorCode(err) == db.UniqueViolation {
  63  			ctx.JSON(http.StatusForbidden, errorResponse(err))
  64  			return
  65  		}
  66  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  67  		return
  68  	}
  69  
  70  	rsp := newUserResponse(user)
  71  	ctx.JSON(http.StatusOK, rsp)
  72  }
  73  
  74  type loginUserRequest struct {
  75  	Username string `json:"username" binding:"required,alphanum"`
  76  	Password string `json:"password" binding:"required,min=6"`
  77  }
  78  
  79  type loginUserResponse struct {
  80  	SessionID             uuid.UUID    `json:"session_id"`
  81  	AccessToken           string       `json:"access_token"`
  82  	AccessTokenExpiresAt  time.Time    `json:"access_token_expires_at"`
  83  	RefreshToken          string       `json:"refresh_token"`
  84  	RefreshTokenExpiresAt time.Time    `json:"refresh_token_expires_at"`
  85  	User                  userResponse `json:"user"`
  86  }
  87  
  88  func (server *Server) loginUser(ctx *gin.Context) {
  89  	var req loginUserRequest
  90  	if err := ctx.ShouldBindJSON(&req); err != nil {
  91  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  92  		return
  93  	}
  94  
  95  	user, err := server.store.GetUser(ctx, req.Username)
  96  	if err != nil {
  97  		if errors.Is(err, db.ErrRecordNotFound) {
  98  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  99  			return
 100  		}
 101  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 102  		return
 103  	}
 104  
 105  	err = util.CheckPassword(req.Password, user.HashedPassword)
 106  	if err != nil {
 107  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
 108  		return
 109  	}
 110  
 111  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
 112  		user.Username,
 113  		user.Role,
 114  		server.config.AccessTokenDuration,
 115  		token.TokenTypeAccessToken,
 116  	)
 117  	if err != nil {
 118  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 119  		return
 120  	}
 121  
 122  	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
 123  		user.Username,
 124  		user.Role,
 125  		server.config.RefreshTokenDuration,
 126  		token.TokenTypeRefreshToken,
 127  	)
 128  	if err != nil {
 129  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 130  		return
 131  	}
 132  
 133  	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
 134  		ID:           refreshPayload.ID,
 135  		Username:     user.Username,
 136  		RefreshToken: refreshToken,
 137  		UserAgent:    ctx.Request.UserAgent(),
 138  		ClientIp:     ctx.ClientIP(),
 139  		IsBlocked:    false,
 140  		ExpiresAt:    refreshPayload.ExpiredAt,
 141  	})
 142  	if err != nil {
 143  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
 144  		return
 145  	}
 146  
 147  	rsp := loginUserResponse{
 148  		SessionID:             session.ID,
 149  		AccessToken:           accessToken,
 150  		AccessTokenExpiresAt:  accessPayload.ExpiredAt,
 151  		RefreshToken:          refreshToken,
 152  		RefreshTokenExpiresAt: refreshPayload.ExpiredAt,
 153  		User:                  newUserResponse(user),
 154  	}
 155  	ctx.JSON(http.StatusOK, rsp)
 156  }
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

## Source: token/jwt_maker.go

```
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

## Source: token/payload.go

```
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

## Source: util/password.go

```
   1  package util
   2  
   3  import (
   4  	"fmt"
   5  
   6  	"golang.org/x/crypto/bcrypt"
   7  )
   8  
   9  // HashPassword returns the bcrypt hash of the password
  10  func HashPassword(password string) (string, error) {
  11  	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
  12  	if err != nil {
  13  		return "", fmt.Errorf("failed to hash password: %w", err)
  14  	}
  15  	return string(hashedPassword), nil
  16  }
  17  
  18  // CheckPassword checks if the provided password is correct or not
  19  func CheckPassword(password string, hashedPassword string) error {
  20  	return bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(password))
  21  }
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
  10  	CreateToken(username string, role string, duration time.Duration, tokenType TokenType) (string, *Payload, error)
  11  
  12  	// VerifyToken checks if the token is valid or not
  13  	VerifyToken(token string, tokenType TokenType) (*Payload, error)
  14  }
```

## Source: api/middleware.go

```
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

## Source: gapi/rpc_create_user.go

```
   1  package gapi
   2  
   3  import (
   4  	"context"
   5  	"time"
   6  
   7  	"github.com/hibiken/asynq"
   8  	db "github.com/techschool/simplebank/db/sqlc"
   9  	"github.com/techschool/simplebank/pb"
  10  	"github.com/techschool/simplebank/util"
  11  	"github.com/techschool/simplebank/val"
  12  	"github.com/techschool/simplebank/worker"
  13  	"google.golang.org/genproto/googleapis/rpc/errdetails"
  14  	"google.golang.org/grpc/codes"
  15  	"google.golang.org/grpc/status"
  16  )
  17  
  18  func (server *Server) CreateUser(ctx context.Context, req *pb.CreateUserRequest) (*pb.CreateUserResponse, error) {
  19  	violations := validateCreateUserRequest(req)
  20  	if violations != nil {
  21  		return nil, invalidArgumentError(violations)
  22  	}
  23  
  24  	hashedPassword, err := util.HashPassword(req.GetPassword())
  25  	if err != nil {
  26  		return nil, status.Errorf(codes.Internal, "failed to hash password: %s", err)
  27  	}
  28  
  29  	arg := db.CreateUserTxParams{
  30  		CreateUserParams: db.CreateUserParams{
  31  			Username:       req.GetUsername(),
  32  			HashedPassword: hashedPassword,
  33  			FullName:       req.GetFullName(),
  34  			Email:          req.GetEmail(),
  35  		},
  36  		AfterCreate: func(user db.User) error {
  37  			taskPayload := &worker.PayloadSendVerifyEmail{
  38  				Username: user.Username,
  39  			}
  40  			opts := []asynq.Option{
  41  				asynq.MaxRetry(10),
  42  				asynq.ProcessIn(10 * time.Second),
  43  				asynq.Queue(worker.QueueCritical),
  44  			}
  45  
  46  			return server.taskDistributor.DistributeTaskSendVerifyEmail(ctx, taskPayload, opts...)
  47  		},
  48  	}
  49  
  50  	txResult, err := server.store.CreateUserTx(ctx, arg)
  51  	if err != nil {
  52  		if db.ErrorCode(err) == db.UniqueViolation {
  53  			return nil, status.Error(codes.AlreadyExists, err.Error())
  54  		}
  55  		return nil, status.Errorf(codes.Internal, "failed to create user: %s", err)
  56  	}
  57  
  58  	rsp := &pb.CreateUserResponse{
  59  		User: convertUser(txResult.User),
  60  	}
  61  	return rsp, nil
  62  }
  63  
  64  func validateCreateUserRequest(req *pb.CreateUserRequest) (violations []*errdetails.BadRequest_FieldViolation) {
  65  	if err := val.ValidateUsername(req.GetUsername()); err != nil {
  66  		violations = append(violations, fieldViolation("username", err))
  67  	}
  68  
  69  	if err := val.ValidatePassword(req.GetPassword()); err != nil {
  70  		violations = append(violations, fieldViolation("password", err))
  71  	}
  72  
  73  	if err := val.ValidateFullName(req.GetFullName()); err != nil {
  74  		violations = append(violations, fieldViolation("full_name", err))
  75  	}
  76  
  77  	if err := val.ValidateEmail(req.GetEmail()); err != nil {
  78  		violations = append(violations, fieldViolation("email", err))
  79  	}
  80  
  81  	return violations
  82  }
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
   9  	"github.com/techschool/simplebank/token"
  10  	"github.com/techschool/simplebank/util"
  11  	"github.com/techschool/simplebank/val"
  12  	"google.golang.org/genproto/googleapis/rpc/errdetails"
  13  	"google.golang.org/grpc/codes"
  14  	"google.golang.org/grpc/status"
  15  	"google.golang.org/protobuf/types/known/timestamppb"
  16  )
  17  
  18  func (server *Server) LoginUser(ctx context.Context, req *pb.LoginUserRequest) (*pb.LoginUserResponse, error) {
  19  	violations := validateLoginUserRequest(req)
  20  	if violations != nil {
  21  		return nil, invalidArgumentError(violations)
  22  	}
  23  
  24  	user, err := server.store.GetUser(ctx, req.GetUsername())
  25  	if err != nil {
  26  		if errors.Is(err, db.ErrRecordNotFound) {
  27  			return nil, status.Errorf(codes.NotFound, "user not found")
  28  		}
  29  		return nil, status.Errorf(codes.Internal, "failed to find user")
  30  	}
  31  
  32  	err = util.CheckPassword(req.Password, user.HashedPassword)
  33  	if err != nil {
  34  		return nil, status.Errorf(codes.NotFound, "incorrect password")
  35  	}
  36  
  37  	accessToken, accessPayload, err := server.tokenMaker.CreateToken(
  38  		user.Username,
  39  		user.Role,
  40  		server.config.AccessTokenDuration,
  41  		token.TokenTypeAccessToken,
  42  	)
  43  	if err != nil {
  44  		return nil, status.Errorf(codes.Internal, "failed to create access token")
  45  	}
  46  
  47  	refreshToken, refreshPayload, err := server.tokenMaker.CreateToken(
  48  		user.Username,
  49  		user.Role,
  50  		server.config.RefreshTokenDuration,
  51  		token.TokenTypeRefreshToken,
  52  	)
  53  	if err != nil {
  54  		return nil, status.Errorf(codes.Internal, "failed to create refresh token")
  55  	}
  56  
  57  	mtdt := server.extractMetadata(ctx)
  58  	session, err := server.store.CreateSession(ctx, db.CreateSessionParams{
  59  		ID:           refreshPayload.ID,
  60  		Username:     user.Username,
  61  		RefreshToken: refreshToken,
  62  		UserAgent:    mtdt.UserAgent,
  63  		ClientIp:     mtdt.ClientIP,
  64  		IsBlocked:    false,
  65  		ExpiresAt:    refreshPayload.ExpiredAt,
  66  	})
  67  	if err != nil {
  68  		return nil, status.Errorf(codes.Internal, "failed to create session")
  69  	}
  70  
  71  	rsp := &pb.LoginUserResponse{
  72  		User:                  convertUser(user),
  73  		SessionId:             session.ID.String(),
  74  		AccessToken:           accessToken,
  75  		RefreshToken:          refreshToken,
  76  		AccessTokenExpiresAt:  timestamppb.New(accessPayload.ExpiredAt),
  77  		RefreshTokenExpiresAt: timestamppb.New(refreshPayload.ExpiredAt),
  78  	}
  79  	return rsp, nil
  80  }
  81  
  82  func validateLoginUserRequest(req *pb.LoginUserRequest) (violations []*errdetails.BadRequest_FieldViolation) {
  83  	if err := val.ValidateUsername(req.GetUsername()); err != nil {
  84  		violations = append(violations, fieldViolation("username", err))
  85  	}
  86  
  87  	if err := val.ValidatePassword(req.GetPassword()); err != nil {
  88  		violations = append(violations, fieldViolation("password", err))
  89  	}
  90  
  91  	return violations
  92  }
```

## Source: token/jwt_maker_test.go

```
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

## Source: token/paseto_maker_test.go

```
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

(11 further tests executed the change and are checked too; not listed.)
