# exp07_state — adversarial fixture for the STATE join

`Processor.run(item)` is the target. Its behavior depends on nothing in its arguments:

| receiver / global state | continuation | exit |
|---|---|---|
| `enabled=True`, `settings.STRICT=False` | `validate → persist` | returned |
| `enabled=True`, `settings.STRICT=True` | `validate → audit → persist` | returned |
| `enabled=False` | `skip` | returned |
| `enabled=True`, `repo.closed=True` | `validate → persist` **raises** `RepositoryClosed` | raised |

The seed test (`test_pipeline.py`) runs a real `Pipeline` with a real `Processor(enabled=True)`
whose `run` is replaced by an instance-attribute stand-in, so the seam exposes the receiver
state. Every fragment test calls `run("item-1")` with the same argument. `VALUE` cannot tell
the fragments apart; `STATE` must. `groundtruth/` holds whole executions for three states.
