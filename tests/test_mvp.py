"""MVP pieces on the fixture: repo-level graph, change mapping, and the probe loop end to end
with a recorded writer inside the sandbox. Skips the confined parts where no OS sandbox
exists on the host."""

import sys
from pathlib import Path

import pytest

from diffgenome.change import changes_from_diff, parse_unified_diff
from diffgenome.collect.py_symbols import PythonSymbolIndex
from diffgenome.compose import build_corpus
from diffgenome.graph import BehavioralGraph, build_graph
from diffgenome.llm import RecordedProbeWriter
from diffgenome.model import EvidenceKind, JoinStrength, Stimulus
from diffgenome.probe import ProbeRunner, run_probe_loop, select_objectives
from diffgenome.sandbox import Workspace, host_supports_confinement
from tests.test_collector import FIXTURE, trace

PLACE = "py:shop.order_service.OrderService.place"
RESERVE = "py:shop.inventory_service.InventoryService.reserve"


@pytest.fixture(scope="module")
def graph(tmp_path_factory: pytest.TempPathFactory) -> BehavioralGraph:
    return build_graph(build_corpus(list(trace(FIXTURE, tmp_path_factory.mktemp("g")).values())))


def test_graph_merges_evidence_without_flattening(graph: BehavioralGraph) -> None:
    kinds = {k for _, _, k in graph.edges}
    assert {EvidenceKind.OBSERVED, EvidenceKind.COMPOSED, EvidenceKind.INTERNAL_GAP} <= kinds
    composed = graph.edges[
        ("py:shop.controller.OrderController.place_order", PLACE, EvidenceKind.COMPOSED)
    ]
    assert composed.best_join is JoinStrength.VALUE
    assert composed.joins[JoinStrength.ARG_SHAPE] >= 1  # weaker alternatives kept, not dropped
    assert len(composed.evidence) == 2 and len(composed.executions) >= 3
    insp = graph.inspect(PLACE)
    assert any(
        e.callee == RESERVE and e.kind is EvidenceKind.INTERNAL_GAP for _, e in insp.downstream
    )
    assert len(insp.tests) == 3
    assert insp.outcomes["returned"] == 2 and insp.outcomes["raised"] == 1


def test_neighborhood_metrics_are_provisional_and_explicit(graph: BehavioralGraph) -> None:
    m = graph.neighborhood([PLACE], up=2, down=3).metrics()
    assert m.internal_gaps == 1 and m.unresolved_boundaries == 2 and m.external_boundaries == 2
    assert m.denominator == m.observed + m.composed + m.internal_gaps + m.unresolved_boundaries
    assert "denominator_provisional" in m.as_dict()


def test_diff_lines_map_to_innermost_functions() -> None:
    index = PythonSymbolIndex(FIXTURE, [FIXTURE], [FIXTURE / "tests"])
    diff = (
        "--- a/shop/order_service.py\n+++ b/shop/order_service.py\n@@ -25,2 +25,3 @@\n"
        "--- a/README.md\n+++ b/README.md\n@@ -1 +1,2 @@\n"
    )
    assert [r.path for r in parse_unified_diff(diff)] == ["README.md", "shop/order_service.py"]
    cs = changes_from_diff(diff, index, "test")
    assert cs.symbols == [PLACE]
    assert cs.unmapped_paths == ["README.md"]


def test_objectives_prefer_gaps_near_the_change(graph: BehavioralGraph) -> None:
    nb = graph.neighborhood([PLACE], up=2, down=3)
    [o] = select_objectives(nb, graph, 3)
    assert (o.kind, o.target, o.caller, o.distance) == ("internal_gap", RESERVE, PLACE, 1)
    assert o.seam_args[0][:2] == ("arg0", "list[2]")


@pytest.mark.skipif(not host_supports_confinement(), reason="no OS sandbox on this host")
def test_probe_loop_closes_a_gap_under_confinement(graph: BehavioralGraph, tmp_path: Path) -> None:
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    (recorded / "01.py").write_text(
        "from unittest.mock import MagicMock, patch\n"
        "from shop.inventory_service import InventoryService\n"
        "def test_reserve():\n"
        "    response = MagicMock(); response.status = 201\n"
        "    cm = MagicMock(); cm.__enter__.return_value = response\n"
        "    with patch('urllib.request.urlopen', return_value=cm):\n"
        "        InventoryService('http://inventory.local').reserve(['A', 'B'])\n"
    )
    ws = Workspace.create(FIXTURE, tmp_path / "ws")
    try:
        from diffgenome.collect.py_runtime import PytestRuntime

        runtime = PytestRuntime(FIXTURE, Path(sys.executable), ".", "tests", "tests", [])
        runtime.prepare(ws)
        runner = ProbeRunner(ws, runtime)
        index = PythonSymbolIndex(FIXTURE, [FIXTURE], [FIXTURE / "tests"])
        nb = graph.neighborhood([PLACE], up=2, down=3)
        attempts, corpus = run_probe_loop(
            graph, nb, index, RecordedProbeWriter(recorded), runner, tmp_path / "out", 1, 1, 2, 3
        )
    finally:
        ws.destroy()
    [a] = attempts
    assert a.verdict == "accepted", a.reasons
    assert a.metrics_before and a.metrics_after
    assert a.metrics_before.internal_gaps == 1 and a.metrics_after.internal_gaps == 0
    assert a.metrics_after.strong_joins == a.metrics_before.strong_joins + 1
    assert all(e.stimulus is Stimulus.GENERATED_PROBE for e in a.executions)
    after = build_graph(corpus)
    edge = after.edges[(PLACE, RESERVE, EvidenceKind.COMPOSED)]
    assert edge.probe_derived and edge.best_join is JoinStrength.VALUE
    # The probe's own patch of urlopen is an external boundary, never crossed.
    assert (RESERVE, "py:urllib.request.urlopen", EvidenceKind.EXTERNAL_BOUNDARY) in after.edges
    assert not any(k is EvidenceKind.OS_BOUNDARY for _, _, k in after.edges)


def test_graph_round_trips_through_json_with_provenance(
    graph: BehavioralGraph, tmp_path: Path
) -> None:
    import json

    from diffgenome.report import render_map_slice

    doc = graph.to_json()
    loaded = BehavioralGraph.from_json(json.loads(json.dumps(doc)))
    assert loaded.corpus is None
    assert set(loaded.edges) == set(graph.edges)
    for key, e in graph.edges.items():
        f = loaded.edges[key]
        assert f.best_join == e.best_join and f.executions == e.executions and f.rules == e.rules
        assert [(x.site, x.fragment, x.join, x.alternates) for x in f.evidence] == [
            (x.site, x.fragment, x.join, x.alternates) for x in e.evidence
        ]
    assert (
        loaded.neighborhood([PLACE], up=2, down=3).metrics().as_dict()
        == graph.neighborhood([PLACE], up=2, down=3).metrics().as_dict()
    )
    slice_ = render_map_slice(loaded, [PLACE])
    assert "⇢ shop.pricing_service.PricingService.quote" in slice_ and "→ [gap]" in slice_
    assert render_map_slice(graph, [PLACE]) == slice_  # deterministic and source-independent
