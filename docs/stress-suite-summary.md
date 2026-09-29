# Stress suite summary: Experiments 08 to 12

All runs are local. Nothing was pushed, Sydes was not modified or run, and the targets were not
modified. Every proposal comes from a fresh isolated Opus instance that read only its bundle.
Statuses come from shown tests only.

## Comparison

| case | shape | held-out exact | all exact | confidently wrong | indeterminate | verified decisions | verified transitions | regions | new core concept forced |
|---|---|---|---|---|---|---|---|---|---|
| Exp 08 simplebank transfer (Go) | input and guard | — (no holdout) | 11/11 paths | 0 | 0 | 3 (D5, D8, D9, after the later recheck) | — | 0 | — |
| Exp 09 Kokoro model manager (Python) | state transitions | **4/4** | 13/13 | 0 | 0 | 4/16 | 7/10 | 0 | — |
| Exp 10A Baserow v1 (frozen) | relation and order | 0/2 | 0/5 | 0 | 5 | 0/7 | 0/2 | — | (tool failures) |
| Exp 10A v2 (Outcome + boundary bindings) | | 0/2 | 0/5 | **5** | 0 | 3/7 | 3/5 | — | — |
| Exp 10A v3 (occurrence structure) | | 0/2 | 0/5 | 0 | 5 | 1/7 | 2/2 | — | — |
| Exp 10A v4 (occurrence binding) | | **2/2** (17/17 occurrences) | 3/5 | 2 (in-sample) | 0 | 3/7 | 0/0 | 4 | per-occurrence facts |
| Exp 11 Case B RBAC (Go) | scalar, gRPC | 1/2 (diagnostic 2/2) | 2/7 (diagnostic 7/7) | 0 (5 before B-F5) | 5 | 5/28 | 0/0 | 0 | none |
| Exp 12 Case C token type (Go) | scalar, 3 entry points | 0/3 (diagnostic 3/3) | 1/20 (diagnostic 20/20) | 0 | 19 | 11/55 | 0/22 | 0 | none |

The "diagnostic" figures are not scores. They are the same proposal with its one proposer or
format failure neutralized: descriptive `calls` in B, missing evidence in C.

## Regression

After every generic fix in these passes, Experiment 09 (main genome and 4 controls) showed 0
differences: 13/13, withheld 4/4, stateless 3/13. Experiment 08 was identical. Baserow v2, v3
and v4 with their controls were identical.

## Answers

**A. Repetition.** Deterministic structure plus per-occurrence binding is sufficient. On Baserow
it predicted every withheld field occurrence (17/17) and both withheld tests. Neither B nor C
used or needed repetition. No case showed a need for item identity carried across calls, a
collection, or `for_each`.

**B. Baserow.** The genome still cannot *derive* the base DataError. It predicts every per-field
decision, but the importer's order comes from dependency levels: a relation over fields, and a
derived order over that relation. The consumer lands on the same level as the linked table's
formula primary at base and after it at head. "Base raises DataError" therefore remains the
model's claim, correct 5/5, not a genome consequence. Relations and derived order are still
unbuilt, with one supporting case.

**C. RBAC.** The real #103 needs no relation abstraction. The role is a scalar; one endpoint
passes a literal list of two roles; the ownership rule is a scalar predicate. The proposer used
none, and the diagnostic shows the scalar genome predicts all 7 tests, including the new banker
case.

**D. Token type.** Yes. The scalar, boundary and outcome genome expresses one rule:

| step | how |
|---|---|
| stamp the type at creation | transition |
| each entry point sets the expected type | scenario input |
| compare the two | the verified type check |

It generalizes to the withheld HTTP, gRPC and JWT cases in the diagnostic (3/3). The scored
result is limited only by a proposer omission (no evidence on 59 items), not by the
representation.

**E. The smallest remaining unsupported classes**, from the three real changes:
1. **Value identity between two call boundaries.** This covers the role at token creation
   equalling the role checked later (B), and the issued type equalling the expected type (C).
   The collector already records it as equal digests; the genome has no binding for it. Small
   enum and literal decoding would also cover C's type values and B's gRPC status codes.
   Outcome sees `*status.Error` but not `PermissionDenied` vs `NotFound`, and HTTP status codes
   are invisible. This touches the digest-domain decision from the Step 2 design.
2. **Relations with a derived order** (Baserow's dependency levels). This is needed only to
   *derive* failures caused by ordering. It still has one supporting case.

Everything else observed was tooling, and was fixed and tested:
- checker bugs: exit-kind prefix, JSON literals, unflagged repetition;
- one format ambiguity: descriptive vs executed branch `calls`;
- two proposer failures: over-simplified dispatch in Baserow, missing evidence in C.

**Open decisions for you:**
- Should prediction use *supported* items whose shown-test replay disagreed (Baserow v4 policy)?
- Should branch `calls` be descriptive, executed, or split into two fields (B-F4)?
- Unsalted or salted digests, which decides how value identity and literal decoding can work?
