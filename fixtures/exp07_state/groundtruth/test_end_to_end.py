"""Whole executions, used only as ground truth: never part of the reconstruction corpus."""

import pytest
from proc import settings
from proc.pipeline import Pipeline
from proc.processor import Processor
from proc.repository import Repository


def test_pipeline_enabled_end_to_end() -> None:
    assert Pipeline(Processor(Repository(), enabled=True)).execute("item-1") == {
        "item": "item-1",
        "result": "stored:item-1",
    }


def test_pipeline_strict_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRICT", True)
    assert (
        Pipeline(Processor(Repository(), enabled=True)).execute("item-1")["result"]
        == "stored:item-1"
    )


def test_pipeline_disabled_end_to_end() -> None:
    assert (
        Pipeline(Processor(Repository(), enabled=False)).execute("item-1")["result"]
        == "skipped:item-1"
    )
