"""The diffgenome-change/1 integration artifact: deterministic, self-contained, no internals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from diffgenome.api import load_change_artifact
from diffgenome.change_artifact import FORMAT, build_change_artifact, dumps
from diffgenome.compose import build_corpus
from diffgenome.graph import build_graph
from tests.test_collector import trace
from tests.test_exp07 import EXECUTE, FIXTURE, RUN


@pytest.fixture(scope="module")
def artifact(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    runs = list(trace(FIXTURE, tmp_path_factory.mktemp("art")).values())
    graph = build_graph(build_corpus(runs))

    def build() -> dict[str, Any]:
        return build_change_artifact(
            graph, [RUN], up=3, down=4, change_spec="git diff HEAD", runtime="python/pytest",
            repo="fixture", revision=None, budget={"writer": "none", "probes_requested": 0},
            probes=[], notes=["n"],
        )  # fmt: skip

    a, b = build(), build()
    a.pop("generated_at"), b.pop("generated_at")
    assert a == b  # deterministic
    return a


def test_shape_and_provenance(artifact: dict[str, Any], tmp_path: Path) -> None:
    assert artifact["format"] == FORMAT
    assert artifact["change"]["symbols"] == [RUN]
    nodes = {n["id"]: n for n in artifact["nodes"]}
    assert nodes[RUN]["changed"] and nodes[RUN]["file"] == "proc/processor.py"
    assert nodes[RUN]["origin"] == "repo" and nodes[RUN]["executed_by"] == 4
    edges = {(e["caller"], e["callee"]): e for e in artifact["edges"]}
    seam = edges[(EXECUTE, RUN)]
    assert seam["evidence"] == "composed" and seam["join"] == "STATE" and seam["state"] == "matched"
    assert seam["exit"] == "same"
    # provenance: the seed that exposed the seam and the fragment that continued it
    assert seam["executions"] == [
        "tests/test_pipeline.py::test_execute_wraps_processor_result",
        "tests/test_processor.py::test_run_enabled_persists",
    ]
    down = edges[(RUN, "py:proc.processor.Processor.persist")]
    assert down["evidence"] == "observed" and down["join"] is None and down["state"] == "n/a"
    # the composer's rejections on the seam are visible, with reasons, not internals
    rejected = [r for r in artifact["rejected_candidates"] if r["target"] == RUN]
    assert {r["reason"].split(":")[0] for r in rejected} == {"state conflict", "exit conflict"}
    assert artifact["ambiguous_seams"][0]["rejected_candidates"] == 3
    assert artifact["facts"]["joins"]["STATE"] == 1
    assert all(e["stimulus"] == "existing_test" for e in artifact["executions"])
    # round trip through the file API
    path = tmp_path / "diffgenome-change.json"
    path.write_text(dumps(artifact))
    assert load_change_artifact(path)["edges"] == artifact["edges"]
    text = json.dumps(artifact)
    for internal in ("NodeRef", "Evidence(", "JoinAttempt", "<diffgenome"):
        assert internal not in text
