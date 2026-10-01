"""Pruning a trace to the change keeps everything the runtime-evidence contract reads."""

from __future__ import annotations

from dataclasses import replace

from diffgenome.collect.prune import prune_to_focus
from diffgenome.model import BranchObs, CallNode, SubstitutionMechanism, SubstitutionNode
from diffgenome.runtime_evidence import build_runtime_evidence
from tests.test_runtime_evidence import MECH, _change, _ex, _Index


def _tree() -> tuple[list, list[BranchObs]]:
    nodes = [
        CallNode(0, None, "py:tests.test_x", 0),
        CallNode(1, 0, "py:app.setup", 0),  # unrelated subtree
        CallNode(2, 1, "py:lib.deep", 0),
        CallNode(3, 0, "py:app.handler", 0),
        CallNode(4, 3, "py:app.deco.<locals>.wrapper", 0),
        CallNode(5, 4, "py:app.service", 0, outcome="returned"),  # focus
        CallNode(6, 5, "py:app.deco.<locals>.inner", 0),
        SubstitutionNode(7, 6, 0, SubstitutionMechanism.MOCK_OBJECT, None, "py:db.save", "attr"),
        CallNode(8, 5, "py:app.helper", 0),
        CallNode(9, 8, "py:app.helper2", 0),
        CallNode(10, 9, "py:app.helper3", 0),  # depth 3 below focus: dropped
        CallNode(11, 0, "py:app.teardown", 0),
    ]
    branches = [BranchObs("br:focus", True, 5, 6), BranchObs("br:setup", False, 2, 3)]
    return nodes, branches


def test_keeps_chain_focus_and_nearby_callees_drops_the_rest() -> None:
    nodes, branches = _tree()
    kept, kept_branches, dropped = prune_to_focus(nodes, branches, {"py:app.service"})
    syms = [getattr(n, "symbol", "sub") for n in kept]
    assert syms == [
        "py:tests.test_x", "py:app.handler", "py:app.deco.<locals>.wrapper", "py:app.service",
        "py:app.deco.<locals>.inner", "sub", "py:app.helper", "py:app.helper2",
    ]
    assert dropped == 4
    # dense ids in the original order, parents remapped
    assert [n.id for n in kept] == list(range(len(kept)))
    assert all(n.parent is None or n.parent < n.id for n in kept)
    assert kept_branches == (BranchObs("br:focus", True, 3, 6),)


def test_no_focus_hit_keeps_only_the_root() -> None:
    nodes, branches = _tree()
    kept, kept_branches, _ = prune_to_focus(nodes, branches, {"py:app.absent"})
    assert [n.id for n in kept] == [0] and kept_branches == ()


def test_runtime_evidence_is_identical_on_pruned_traces() -> None:
    # a changed test function is in the focus too, so noise starts three levels below it
    noise = (
        CallNode(99, 0, "py:app.unrelated", 0), CallNode(100, 99, "py:lib.noise", 0),
        CallNode(101, 100, "py:lib.deeper", 0), CallNode(102, 101, "py:lib.deepest", 0),
    )
    base = (_ex("t::a", "returned", True, False), _ex("t::b", "raised:py:ValueError", False, True))
    full = [replace(ex, nodes=(*ex.nodes, *noise)) for ex in base]
    focus = set(_change().symbols)
    pruned = []
    for ex in full:
        nodes, branches, dropped = prune_to_focus(ex.nodes, ex.branches, focus)
        assert dropped == 2
        pruned.append(replace(ex, nodes=nodes, branches=branches))
    expected = build_runtime_evidence(full, _change(), _Index(), MECH, [])
    assert build_runtime_evidence(pruned, _change(), _Index(), MECH, []) == expected
