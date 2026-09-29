# Design note: value identity across call boundaries, literal identity, branch `calls`, prediction eligibility

Status: built (see `docs/experiment-13-value-identity.md`). Language-neutral. Additive, except
for the `Branch.calls` decision (section 4), whose migration is explicit.

## 1. The gap

Two real changes needed the same thing, and neither could state it:
- **Case B (RBAC):** the role given at token creation is the role checked later.
- **Case C (token type):** the type issued at creation is compared with the type expected at
  verification.

The collector already records both as digest equality or inequality. The genome could not
bind two boundaries, so the role and the type were scenario assumptions.

## 2. What is bound, and how

**A boundary definition, evaluated per occurrence.** A binding names `(entity, point)`, with
point `arg:<name>` or `result`. It never names a single call. Its value is drawn from
occurrences, under an explicit **scope**:

| scope | value | ambiguity |
|---|---|---|
| `call` (default, as before) | the boundary of the call being judged, the deciding call | none: one call |
| `execution` | the boundary's value in the occurrences of that entity that ran **before** the point of evaluation, in the same execution (test) | if they carry **different** identities, the value is *ambiguous* (unknown), never a guess |

There is no cross-execution or cross-request scope. A token that persists across requests
would need both boundaries inside one observed execution, which is what these tests do.

**Opaque identity.** A new boundary kind `identity` gives the variable an opaque value: the
digest, which the genome never decodes. Predicates compare identities with `==` and `!=` only.

**Identity claim = one variable observed at two or more boundaries.** `observed_as` may be a
list. A variable with at least two `identity` bindings claims that *every observation of it
in one execution is the same value*. This is **equality, not flow**: it never claims that B was
copied from A.

**Why this and not a separate object.** A separate `{left, right}` object duplicates naming,
evidence and status, and cannot feed predicates. A variable already carries `derived_by`,
`evidence` and `status`, and is what decisions read. Two bindings on one variable say exactly
"the same semantic value appears here and there".

**Status of an identity claim** (checked on shown executions only):

| status | rule | why |
|---|---|---|
| rejected | in some execution, every side has an unambiguous value and two sides differ | positive evidence against equality |
| verified | equal in at least 2 executions, **and** at least 2 distinct identities among those executions | the contrast rules out a coincidence of a constant: if every test used one role, "equal" would only say "the default role is the default role" |
| supported | equal wherever both sides were seen, but fewer than 2 executions or only one distinct value | |
| unknown (reason recorded) | no execution in which all sides are present and unambiguous | missing evidence stays missing |

**Privacy.** No raw value is captured or shown. Identities are the collector's existing digests.

## 3. Literal identity (separate from identity)

`banker` vs `depositor` and access vs refresh are *meanings*. Comparing a runtime value with a
source literal is a separate binding kind, `equals_literal`, giving a boolean:

```json
{"at": {"entity": "…", "point": "arg:role"}, "kind": "equals_literal",
 "literal": {"lang": "go", "type": "string", "value": "banker",
             "source": {"file": "util/role.go", "line": 5}}}
```

The checker:
1. confirms the literal occurs on the cited source line;
2. computes the runtime's canonical form, for example Go `string:"banker"` or `uint8:1`, and
   Python `str:'banker'`;
3. digests it with the collector's scheme and compares it with the observed digest.

It is allowed only for:
- bool;
- null;
- integers of at most 64 bits;
- strings of at most 64 characters.

Each must be written literally on a cited line of the target's source. The checker never
enumerates or guesses values; it only confirms or refutes one the proposal cites from source.

**Options for the digest domain:**

| option | how | pros | cons |
|---|---|---|---|
| A. unsalted global digest (current) | sha256 of the canonical form | static and runtime comparison trivial; old artifacts stay valid | low-entropy values can be guessed |
| B. analysis-local salt | one secret salt per analysis, shared by static and runtime sides | guessing needs the salt | all three collectors need the salt plumbed through; all old artifacts invalid |
| C. allowlisted decoding | capture bool, null, small enums, status codes as values | no digest tricks | captures values; new collector code per runtime |

**Recommendation: keep A for now, with `equals_literal` restricted as above, and plan B as
hardening.** The guessing risk already exists in every persisted artifact: `9f99e2` is
`string:"banker"`, verified while writing this note. `equals_literal` adds no new exposure,
because it only compares against literals the source itself contains. B is the right next
step and is recorded as an open item. It is not needed for equality, which works under any
fixed scheme.

**Not handled: gRPC or HTTP status codes.** A code is a field *inside* an error value whose
digest also covers the message. No boundary carries the code alone, so literal identity
cannot reach it. That stays a separate value-decoding limitation. Outcome is not overloaded.

## 4. `Branch.calls`: decided

- `Procedure.steps`, `Region.steps` and a branch's `steps` are the only executable structure.
- `Branch.calls` is **descriptive** ("reaches", "may call") and is never executed by the
  sequence predictor or the observed-path replay.

The static checks still read it (reachability under the site), and Experiment 08's path
predictor still reads it as the path's description.

**Migration.** A genome written under the old contract ("steps, or if empty its calls") is
migrated explicitly by `migrate_executable_calls(proposals)`. Every branch with `calls` and no
`steps` gets `steps = ["call:X", …]`. It is applied only where a recorded result depended on
it. That was measured before the change, and is listed in the experiment report. It is never
applied to new proposals.

## 5. Prediction eligibility (internal, not a new status)

An item is **eligible for prediction** if it is verified, or it is supported **and has no
recorded observed contradiction**. The contradictions are:
- a replayed outcome sequence that differs on a shown test;
- local disagreement;
- disagreement with stated facts;
- an occurrence-level disagreement.

The semantic status is unchanged. Only eligibility drops. Diagnostics that ask for
`min_status="hypothesis"` still use everything.

Acceptance: **no known contradicted item may drive a determinate prediction.**

## 6. Scenario facts become checkable where bound

A scenario call's facts for a variable bound at that call's boundary (call scope), or within
the execution (execution scope), are compared with the observation, on shown tests only. A
contradiction makes the prediction indeterminate, as occurrence facts already do.

For identity variables the scenario gives *labels*, such as `"access"`, which are never
decoded. The checker only requires the **label pattern** to match the digest pattern: equal
labels where the identities are equal, different labels where they differ.

## 7. Not included

Flow or provenance ("copied from"), cross-execution persistence, relation-valued variables,
derived order, decoding arbitrary values, and status-code capture.
