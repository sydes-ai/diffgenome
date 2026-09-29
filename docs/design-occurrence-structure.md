# Design note: observed execution structure (occurrences and skeleton)

Status: built (`src/diffgenome/structure.py`, checks in `genome_state`). Language-neutral.
Results are in `docs/experiment-10-stress-baserow.md`, under "Step 2b".

## Why

In Case A v2, every prediction was confidently wrong about *where* work happened. The proposer
hoisted per-field calls out of the import function that encloses them. Call nesting and
chronology are runtime facts, not meaning. A proposer should not be free to invent them.

## What the protocol already gives

The existing event protocol is enough. No collector change is needed:
- call node ids are in creation order;
- parents precede children;
- a branch observation names its call node and a `seq` on the same clock;
- every call has an exit.

It does not give runtime call-site ids. Repeated calls are therefore keyed by
*(parent occurrence, entity, ordinal)*, which is available everywhere.

## Two objects, kept apart

**Occurrence graph** (evidence, per execution). This is computed relative to a vocabulary,
the entity names a genome uses.
- Every observed call of a vocabulary entity is an occurrence.
- Its parent is the nearest ancestor call that is also a vocabulary entity. Other frames are
  looked through.
- Its ancestors are all such enclosing entities.
- Its ordinal counts earlier same-entity siblings.
- Its events are its child occurrences and the branch evaluations of its own call, in time
  order.
- Its outcome is the call's exit.

Branch evaluations belong to the occurrence of their own call node. This is what ties a
repeated site's evaluations to a specific call occurrence.

**Skeleton** (a deterministic abstraction over the *shown* executions). It is never built from
withheld ones. It records:
- **Ancestry:** per entity, which vocabulary entities it ran during, and whether it ran with no
  modeled caller (`<root>`), with occurrence and execution counts.
- **Phase order:** per parent entity, pairwise precedence among event families (child
  entities, and own decision sites `site:<id>`). *x before y* means all of x precedes all of y
  in every occurrence holding both. A pair seen in both orders is not an order.
- **Repeated regions:** families that interleave. A region's **head** is a member that starts
  every repetition, with every other member appearing at most once between heads. With a head,
  the order *inside one repetition* is recorded. Without one, only membership is known. No loop
  variable, collection or count semantics are involved.
- **Site ownership:** which entity's own call evaluates each site, and during which entities.

## Checks

- **Prediction placement.** Predictions record their own occurrence tree. A prediction that
  places a call where it was never observed, a decision evaluated in a function where its site
  never was, or two steps in an order observed reversed (between phases, or inside one
  repetition) is **indeterminate**. It is never scored as right or wrong. Only entities the
  skeleton has observed are judged.
- **Procedure structure claims** (`procedure_structure_claims`):
  - *contains*: B runs during A;
  - *evaluates*: a decision's site is evaluated during A;
  - *order*: consecutive steps.

  Each is verified, supported, not established, unobserved, or rejected. **Absence never
  rejects:** a call on a path the tests never took is simply not established. Rejection needs
  positive evidence: *inverted nesting* (every observed A ran during B, yet A's procedure
  places B inside A), or an *observed reversed order*. A rejected claim rejects its procedure.

Absence-based rejection was tried first. It rejected three correct Kokoro procedures, whose
calls sit on paths the tests never took, and was withdrawn before any result was recorded.

## Explicitly not included

`for_each`, loop variables, collections, counts, relation-valued variables, derived orders.
