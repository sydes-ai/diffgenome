"""`diffgenome genome`: scenario resolution, source windows, and the artifact summary exporting
only checked claims."""

from types import SimpleNamespace

from diffgenome.genome import REJECTED, SUPPORTED, VERIFIED, genome_from_proposals
from diffgenome.genome_pipeline import _resolve, _windows, eligible, summary


def test_resolve_full_id_and_unique_suffix() -> None:
    refs = ["TestA/OK", "TestB/OK", "pkg/test_x.py::test_one", "TestA/Bad"]
    assert _resolve("TestA/OK", refs) == "TestA/OK"
    assert _resolve("Bad", refs) == "TestA/Bad"
    assert _resolve("OK", refs) is None  # ambiguous
    assert _resolve("test_one", refs) == "pkg/test_x.py::test_one"
    assert _resolve("missing", refs) is None


def test_windows_small_file_whole_large_file_windowed() -> None:
    small = [f"l{i}" for i in range(10)]
    assert _windows(small, set(), set()) == list(range(1, 11))
    big = ["x = 1"] * 1000
    big[599] = "def test_thing(db):"
    big[600] = "    assert 1"
    big[601] = "def other():"
    keep = _windows(big, {100}, {"test_thing"})
    assert 100 in keep and 88 in keep and 113 not in keep
    assert {600, 601} <= set(keep)
    assert 500 not in keep


def _genome():
    p = {
        "variables": [{"id": "V1", "name": "x", "origin": "input", "evidence": []}],
        "decisions": [
            {"id": f"D{k}", "entity": "f", "site": "br:1", "predicate": "x", "evidence": []}
            for k in range(4)
        ],
        "transitions": [],
    }
    g = genome_from_proposals(p, {}, "m")
    g.decisions[0].status = VERIFIED
    g.decisions[1].status = SUPPORTED
    g.decisions[2].status = SUPPORTED
    g.decisions[2].contradicted = True
    g.decisions[3].status = REJECTED
    return g


def test_summary_exports_only_checked_claims() -> None:
    g = _genome()
    assert [eligible(d) for d in g.decisions] == [True, True, False, False]
    run = SimpleNamespace(
        mech=SimpleNamespace(sites={"br:1": {"file": "a.go", "line": 3, "pred": "x"}})
    )
    ev = {
        "tests": 2,
        "scenarios": 2,
        "consistent": 2,
        "indeterminate": 0,
        "contradicted": 0,
        "site_agreement": {"D1": [True, True], "D4": []},
    }
    s = summary(run, g, ev, "m", {"unknowns": [{"what": "w", "why": "y"}]}, "d", {})  # type: ignore[arg-type]
    assert s["format"] == "diffgenome-genome-summary/1"
    assert [r["id"] for r in s["decision_rules"]] == ["D0", "D1"]
    ev["site_agreement"] = {"D1": [True, False]}  # a supported rule some test disagrees with
    s2 = summary(run, g, ev, "m", {}, "d", {})  # type: ignore[arg-type]
    assert [r["id"] for r in s2["decision_rules"]] == ["D0"]
    assert s["decision_rules"][0]["file"] == "a.go"
    assert s["statuses"]["contradicted_not_exported"] == 1
    assert s["statuses"]["rejected"] == 1
