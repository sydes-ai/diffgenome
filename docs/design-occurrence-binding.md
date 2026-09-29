# Design note: per-occurrence fact binding for a repeated region

Status: built (see "Step 2c" in `docs/experiment-10-stress-baserow.md`). Language-neutral.
Additive: genomes without regions are unchanged.

## The gap

Step 2b showed the gap on Baserow. Inside ONE call of `_import_table_fields`, one repeated
region runs 8 or 9 times, and each occurrence has different facts. Those facts come from the
scenario's input (the fields), not from evolving state. A genome could change facts inside a
call only through transitions. So it had to hard-code the pattern, hoist the work (now a
placement error), or say nothing.

## Challenged alternatives

| alternative | why not |
|---|---|
| per-occurrence variable names (`field3_empty`) | not generative; counts become part of the genome |
| a second procedure for the enclosing entity | procedures are keyed by entity; one entity has one procedure |
| pseudo-entities for each phase | they have no observed occurrences, so the placement check makes them indeterminate, correctly |
| transitions that read a per-test list | a list is a collection: no collection semantics in this pass |
| `for_each` over a relation | needs relation-valued variables, which are not built and not needed here |

## The abstraction

The three kinds of knowledge are kept separate.

| who | supplies |
|---|---|
| **mechanics** (`diffgenome.structure`) | *where* the region lives (its enclosing entity), *what* belongs to it (the families of the observed repeated region), its **head** (the family that starts every repetition), nesting, and the order inside one repetition. Observed occurrence identity is `(region, ordinal)`: the k-th repetition of the region inside one occurrence of the enclosing entity |
| **scenario** (model-read input facts) | for one concrete call: how many occurrences the input produces, and each occurrence's facts, in order |
| **genome** (semantics) | ONE body for the region, the same for every occurrence (decisions, calls, transitions), and what the facts mean |

**Genome element** `regions: [{id, entity, head, steps, evidence}]`. It carries `derived_by`,
`evidence` and `status` like every item.
- `entity` is the enclosing function.
- `head` names the observed family that starts each repetition.
- `steps` is the body, in the procedure step language.

**Procedure step** `"R:<region id>"` in the enclosing entity's procedure marks where the region's
occurrences run. The genome never states a count.

**Scenario:**
`{"entity": A, "facts": {...}, "occurrences": {"<region id>": [{"facts": {...}}, ...]}}`.
The k-th item is occurrence `(region, k)`. An occurrence item may itself carry `occurrences`
for a region reached inside it. There are none in Case A.

**Prediction.** At `R:x` the predictor takes the supplied occurrences of x from the current
scenario item, in order. For each one it:
1. adds that occurrence's facts;
2. runs the body, with its events belonging to the enclosing call's occurrence, as observed;
3. restores every variable that is not bound to receiver or global state.

Occurrence facts do not leak into the next occurrence. State transitions persist. If no
occurrences are supplied for a region the procedure reaches, the prediction is indeterminate
("occurrence facts not supplied"). A count is never guessed.

**Checks:**
- **Region structure** (`procedure_structure_claims`, kind `region`). The region's head must
  be the head of an observed repeated region of its enclosing entity:
  - verified with at least 2 executions;
  - *unobserved* if the entity has no such region;
  - rejected if the head is a family observed in the entity but not repeated there.

  Its body's consecutive steps are order claims *inside one repetition*. Its calls and
  decisions are containment and evaluation claims *during the enclosing entity*.
- **Occurrence facts** (`check_scenario_occurrences`, used by `compare_sequence`). This applies
  to a scenario whose execution is visible to the checker, which means the shown tests only.
  The k-th supplied occurrence is aligned with the k-th observed repetition. Then each supplied
  fact is compared with what that repetition shows:
  - the boundary facts of the calls inside it, for boundary-bound variables;
  - the variables that the body's atomic decisions (`v` / `!v`) bind from their observed
    outcomes in that repetition.

  A contradicted fact makes the prediction indeterminate, because the scenario is wrong about
  its input, and is reported. Confirmed facts are counted as *verified occurrence-bound facts*.
  More or fewer supplied occurrences than observed repetitions is also a contradiction.

## What it does not do

No loop variable, collection, iterator, break or continue, `while`, nested loops, aggregation,
item identity across calls, relation, or derived order.

Held-out scenarios' occurrence facts are claims about an unseen input. Nothing can check them
before execution, exactly like any scenario fact in Experiment 09. A wrong input claim gives a
wrong prediction, and that is recorded as an input error, not hidden.
