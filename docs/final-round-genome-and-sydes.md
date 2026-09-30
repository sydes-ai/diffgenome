# Final round: `diffgenome genome` as a product step, and the Sydes test

All local. Nothing was pushed to any remote, PyPI or upstream. Sydes changes are local commits.
Targets were cloned into scratch at the change's head and never modified.

## 1. What was built

`diffgenome genome --run <diffgenome change output> [--writer …] [--attach]` has four steps. All
of them are generic: no framework, language or case knowledge.

| step | what it does |
|---|---|
| bundle | The v5 proposer instructions (`genome_prompt.py`). Required sites. Observed execution structure. Mechanics of the vocabulary. Event logs. The change's diff, and the sources. |
| propose | `recorded:<proposals.json>`, or `openai[:model]` (one call, JSON output). |
| establish | Statuses from **every** execution that ran the change; every scenario predicted and compared (consistency). |
| summarize | The artifact's `genome` section (`diffgenome-genome-summary/1`). |

**The bundle is generic.**
- **Vocabulary:**
  - the changed functions that executed (read from the traces, not from the artifact's list);
  - the functions nested in them;
  - their observed direct callers and callees.
- **Tests:** every execution that called a changed function. Up to 40 are listed in the bundle,
  one per distinct observed behavior first; all of them are checked.
- **Files:**
  - large files are shown as windows around the vocabulary's lines and the listed tests' bodies;
  - the change's small non-test, non-generated files are added (constants live there, e.g.
    `util/role.go`).

**The summary exports checked claims only:**
- decisions that are **verified**, or **supported** with every test that exercised them agreeing
  with the prediction;
- identity claims (verified or supported, never contradicted);
- literal bindings the checker confirmed on the cited source line;
- verified transitions;
- the consistency count, the counts of what was *not* exported, and the proposer's unknowns.

Rules at a line the change added or modified are marked `at_changed_line`.

**Frozen, as planned:** relations, salting, status codes, compound values.

Fixed while building the pipeline (generic; the regression-suite code paths are unchanged):
- The 40-test cap was alphabetical and dropped behaviors. Selection is now by behavior, and
  establishment always uses every relevant test.
- The artifact's `symbols_never_executed` list can come from another run: the merged Case C
  artifact claimed `authorizeUser` never executed. Executed-ness is now read from the traces.
- A test that enters a changed closure (`authMiddleware.<anon>@21`) now counts as relevant.
- The first summary exported supported decisions whose meaning the checker could not test.
  Now a supported rule needs agreement in every test that exercised it.

## 2. Results through the product command

| case | proposal | tests | consistent | contradicted | indeterminate | verified | exported rules (verified) | identities / literals |
|---|---|---|---|---|---|---|---|---|
| B simplebank #103 RBAC | recorded Opus (Exp 13 v5) | 7 | **7/7** | 0 | 0 | 11 | 24 (10) | `token_username` verified / `"banker"` |
| C simplebank #136 token type | recorded Opus (Exp 13 v5) | 51 run the change, 20 scenarios | **20/20** | 0 | 0 | 13 | 27 (12) | `expected_type` verified / `1`, `2` |
| A Baserow #6069 | recorded Opus (Exp 10 v4) | 5 | 0/5 | 0 | 5 | 3 | 5 (3) | — |
| B, **live GPT-5** on the product bundle | `openai` (gpt-5, 147 s, 40k in / 21k out tokens) | 7 | 0/7 | 0 | 7 | 2 | 9 (2) | — |

**Caveat on the recorded rows.** The recorded Opus proposals were written from the Experiment
10–13 bundles (with held-out tests), not from this command's bundle. They show that the product
establishment reproduces the experiments (B 7/7, C 20/20, Baserow 0 wrong / 5 indeterminate).
They do **not** measure a proposer on the product bundle. Only the GPT-5 row does.

**GPT-5 on the product bundle: safe, but weak.** Every prediction is indeterminate, because its
`authorizeUser` procedure stayed a hypothesis. The checker was right both times:
- It cited `VerifyToken` as *controlled by* the `err != nil` check that follows the call, and
  `hasPermission` as controlled by the predicate `!hasPermission(...)` that contains it.
- It quoted source with `...` ellipses, which match no line.

This is the C-F3 class (unusable evidence). Nothing wrong was predicted or exported: its 9
exported rules are all at sites the traces agree with. The proposer is the weak link, not the
checker. The checker was not loosened.

## 3. Sydes

Sydes (local commits `cabe6da`, `c9ddcb9`) reads the optional `genome` section and renders
"Checked behavioral rules": rules at changed lines first, each with its status. It also shows
identities, literals, the consistency count, how many claims were withheld, and the top
unknowns. The graph, obligations and verdict are untouched.

**Full record:** `sydes/docs/integration/diffgenome-genome/comparison.md`, with terminals,
rendered variants and result extracts.

**Setup.** Sydes' default provider is a local Ollama `llama3.1`. Its code review failed to
parse in 3 of 4 runs, so a first set of runs was discarded as "no review" and kept only as a
record. The comparison uses OpenAI `gpt-4.1` for Sydes.

| | B #103 | C #136 | A Baserow |
|---|---|---|---|
| Sydes code review, before / after | 0 / 0 findings | 0 / 0 | 0 / 0 |
| verdict | unchanged | unchanged | unchanged |
| Sydes states the change's rule | no | no | no (no structural path at all) |
| genome states it, checked | **yes**: ownership rule at `rpc_update_user.go:29` verified; role match verified | **yes**: type check at `payload.go:54` verified; expected-type identity verified; literals 1 and 2 | the fix's mechanism (deferral, implied-dependency expansion) verified; the DataError ordering is explicitly unmodelled |
| rules predict | 7/7 tests | 20/20 | 0/5 (indeterminate, never wrong) |
| extra wall time | ~0 s (establishment 0.6 s) | ~0 s (0.5 s) | ~0 s (7.5 s) |
| extra model calls | 0 (recorded) | 0 | 0 |

**Answer.** The genome changes the *content* a reviewer gets. For all three changes it is the
only layer that states the changed rule, at the changed line, with a status and a test count.
It changes no conclusion Sydes computes:
- no new issues;
- no false alarms removed, because the review found none either way;
- the verdict is unchanged by design;
- the Baserow DataError is still not derived.

The two things that would turn content into conclusions:
1. give Sydes' code review the checked rules as context;
2. a proposer that cites usable evidence on the product bundle. The one live GPT-5 attempt did
   not.

## 4. PyPI

Not published. Everything was tested and verified locally:
- DiffGenome: 109 tests pass, ruff and mypy are clean. The genome core is unchanged in this
  round, so the regression suite is at the Experiment 13 state.
- Sydes: 1827 tests pass. 3 fail identically without these changes (CBM packaging and the
  Anthropic-client environment).
- The live Sydes runs used the local editable installs.

Per the instruction, publishing was needed only if local verification was impossible.
