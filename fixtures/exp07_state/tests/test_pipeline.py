from unittest.mock import patch

from proc.pipeline import Pipeline
from proc.processor import Processor
from proc.repository import Repository


def test_execute_wraps_processor_result() -> None:
    # The seed: a real Processor whose `run` is replaced on the instance, so the seam sees
    # the receiver's state (enabled=True) while the continuation is not executed here.
    processor = Processor(Repository(), enabled=True)
    with patch.object(processor, "run", autospec=True) as run:
        run.return_value = "stored:item-1"
        assert Pipeline(processor).execute("item-1") == {
            "item": "item-1",
            "result": "stored:item-1",
        }
