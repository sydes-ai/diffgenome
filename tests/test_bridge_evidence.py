"""External-bridge evidence: observed through external code, never "called by" it.

The Node collector (behind DIFFGENOME_EXTERNAL_BRIDGES) keeps one external call node X when a
call into uninstrumented code re-enters repository code B (NestJS CQRS:
`commandBus.execute(command)` -> DeleteUserService.execute). Internally the graph keeps X:
A -> X is OBSERVED (a call seen at its call site) and X -> B is OBSERVED_THROUGH_EXTERNAL.
Publicly `diffgenome-runtime/1` flattens X away: caller A, callee B, `relation:
"through_external"` and `via` describing X. X is never a public caller. Without a bridge,
output is byte-identical to before; a missing `relation` stays unspecified (legacy).

The inputs are the real CQRS traces recorded with the flag off and on (fixtures/bridges).
"""

from __future__ import annotations

import json

import pytest

from diffgenome.change_artifact import EVIDENCE_THROUGH_EXTERNAL, build_change_artifact
from diffgenome.compose import build_corpus
from diffgenome.graph import BehavioralGraph, build_graph
from diffgenome.model import Evidence, EvidenceKind, NodeRef
from diffgenome.projection import project
from diffgenome.report import render_neighborhood
from tests._bridge_cases import (
    FIXTURES,
    SERVICE,
    CqrsIndex,
    contract,
    cqrs_change,
    legacy_outputs,
    trace,
)

BRIDGE = "js:external:CommandBus.execute"
ROOT = (
    "js:tests/diffgenome-cqrs.e2e-spec.ts::"
    "DiffGenome CQRS dispatch dispatches DeleteUserCommand to DeleteUserService"
)
TEST_ARROW = "js:tests/diffgenome-cqrs.e2e-spec.<anon>@9.<anon>@13"


def _graph() -> BehavioralGraph:
    return build_graph(build_corpus([trace("cqrs-flag-on")]))


def _contract() -> dict:
    return contract([trace("cqrs-flag-on")], cqrs_change(), CqrsIndex(), [])


def test_graph_keeps_the_bridge_with_distinct_evidence() -> None:
    kinds = {(e.caller, e.callee): e.kind for e in _graph().edges.values()}
    # the call into external code was seen at its call site
    assert kinds[(TEST_ARROW, BRIDGE)] is EvidenceKind.OBSERVED
    # the service ran while that invocation was active; it was not called by it
    assert kinds[(BRIDGE, SERVICE)] is EvidenceKind.OBSERVED_THROUGH_EXTERNAL
    # nothing else is reclassified
    assert kinds[(ROOT, TEST_ARROW)] is EvidenceKind.OBSERVED
    assert EvidenceKind.EXTERNAL_BOUNDARY not in kinds.values()


def test_contract_flattens_the_bridge_into_via() -> None:
    r = _contract()
    [edge] = [e for e in r["edges"] if e["callee"]["symbol"] == SERVICE]
    assert edge["caller"]["symbol"] == ROOT and edge["caller"]["origin"] == "test"
    assert edge["relation"] == "through_external"
    assert edge["via"] == {
        "symbol": BRIDGE,
        "origin": "external",
        "owner": "CommandBus",
        "member": "execute",
        "arg_shapes": [["DeleteUserCommand"]],
        "exits": {"raised:js:Error": 1},
    }
    assert edge["executions"] == 1 and edge["tests_total"] == 1


def test_changed_function_callers_use_the_same_flattening() -> None:
    [fn] = [f for f in _contract()["changed_functions"] if f["symbol"] == SERVICE]
    [caller] = fn["callers"]
    assert caller["symbol"] == ROOT
    assert caller["relation"] == "through_external" and caller["via"]["symbol"] == BRIDGE
    assert caller["calls"] == 1 and caller["tests"] == 1
    # apart from caller relation/via, the changed function reads exactly as with the flag off
    [off] = [
        f
        for f in contract([trace("cqrs-flag-off")], cqrs_change(), CqrsIndex(), [])[
            "changed_functions"
        ]
        if f["symbol"] == SERVICE
    ]
    strip = {k: v for k, v in fn.items() if k != "callers"}
    assert strip == {k: v for k, v in off.items() if k != "callers"}
    assert [
        {k: v for k, v in c.items() if k not in ("relation", "via")} for c in fn["callers"]
    ] == off["callers"]


def test_the_external_bridge_is_never_a_public_caller() -> None:
    r = _contract()
    callers = [e["caller"] for e in r["edges"]] + [
        c for f in r["changed_functions"] for c in f["callers"]
    ]
    assert callers and all(c["symbol"] != BRIDGE and c["origin"] != "external" for c in callers)
    assert all(e["callee"]["symbol"] != BRIDGE for e in r["edges"])


def test_caller_identity_matches_the_flag_off_run() -> None:
    """The bridge adds relation/via; it never changes who the caller is."""
    off = contract([trace("cqrs-flag-off")], cqrs_change(), CqrsIndex(), [])
    on = _contract()

    def pairs(r: dict) -> set[tuple[str, str]]:
        return {(e["caller"]["symbol"], e["callee"]["symbol"]) for e in r["edges"]}

    assert pairs(on) == pairs(off)
    assert all("relation" not in e and "via" not in e for e in off["edges"])


@pytest.mark.parametrize("name", sorted(legacy_outputs()))
def test_without_a_bridge_output_is_byte_identical(name: str) -> None:
    """Captured before bridge evidence existed: legacy runs must not change at all."""
    assert legacy_outputs()[name] + "\n" == (FIXTURES / f"{name}.json").read_text()


def test_older_graphs_and_traces_still_load() -> None:
    legacy = json.loads((FIXTURES / "legacy-cqrs-graph.json").read_text())
    old = BehavioralGraph.from_json(legacy)
    assert all(e.kind is not EvidenceKind.OBSERVED_THROUGH_EXTERNAL for e in old.edges.values())
    new = BehavioralGraph.from_json(json.loads(json.dumps(_graph().to_json())))
    assert any(e.kind is EvidenceKind.OBSERVED_THROUGH_EXTERNAL for e in new.edges.values())
    assert trace("cqrs-flag-off").nodes  # an old trace deserializes unchanged


def test_through_external_is_a_direct_observation_with_no_rule() -> None:
    site = NodeRef("x", 1)
    Evidence(EvidenceKind.OBSERVED_THROUGH_EXTERNAL, site)
    with pytest.raises(ValueError):
        Evidence(EvidenceKind.OBSERVED_THROUGH_EXTERNAL, site, rule="anything")


def test_artifact_and_report_show_the_distinction() -> None:
    graph = _graph()
    be = project(graph)[(BRIDGE, SERVICE)]
    assert be.through_external_executions and not be.observed_executions
    art = build_change_artifact(
        graph,
        [SERVICE],
        up=3,
        down=3,
        change_spec="cqrs",
        runtime="node",
        repo="r",
        revision=None,
        budget={},
        probes=[],
        notes=[],
    )
    [edge] = [e for e in art["edges"] if e["callee"] == SERVICE]
    # not "observed" (a consumer would read that as a call) and not "composed"
    assert edge["caller"] == BRIDGE and edge["evidence"] == EVIDENCE_THROUGH_EXTERNAL
    text = render_neighborhood(graph.neighborhood([SERVICE]), graph, "n")
    line = next(
        x
        for x in text.splitlines()
        if x.rstrip().split("  tests=")[0].endswith(SERVICE.split(":", 1)[1])
    )
    assert "[through external: CommandBus.execute(DeleteUserCommand)] → " in line
    assert "external:CommandBus.execute → " + SERVICE.split(":", 1)[1] not in text
