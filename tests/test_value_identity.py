# ruff: noqa: E501
"""Value identity across call boundaries and literal identity (docs/design-value-identity.md),
on a synthetic token flow whose digests are built exactly as the Go collector builds them:
a role and a token type are given at creation and seen again at verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from diffgenome.genome import (
    HYPOTHESIS,
    REJECTED,
    SUPPORTED,
    VERIFIED,
    Substrate,
    dumps,
    genome_from_proposals,
)
from diffgenome.genome_state import (
    Identity,
    Mechanics,
    Observations,
    StateSubstrate,
    compare_sequence,
    establish_state,
    identity_claim,
    literal_canonical,
    literal_in_source,
    predict_sequence,
    scoped_value,
)
from diffgenome.model import BranchObs, CallNode, Execution, Stimulus


def _d(c: str) -> str:
    return hashlib.sha256(c.encode()).hexdigest()[:16]


ROLE = {"banker": _d('string:"banker"'), "depositor": _d('string:"depositor"')}
TYPE = {"access": _d("uint8:1"), "refresh": _d("uint8:2")}
SITE = "br:typecheck01"


def _ex(
    name: str, role: str, issued: str, expected: str, extra_issue: str | None = None
) -> Execution:
    nodes: list[Any] = [
        CallNode(0, None, "go:Test", 0),
        CallNode(
            1,
            0,
            "go:token.CreateToken",
            0,
            (("role", "string", ROLE[role]), ("tokenType", "token.TokenType", TYPE[issued])),
        ),
        CallNode(
            2,
            1,
            "go:token.NewPayload",
            0,
            (("role", "string", ROLE[role]), ("tokenType", "token.TokenType", TYPE[issued])),
        ),
    ]
    if extra_issue:  # a second token issued in the same execution, of another type
        nodes.append(
            CallNode(
                3,
                0,
                "go:token.NewPayload",
                0,
                (
                    ("role", "string", ROLE[role]),
                    ("tokenType", "token.TokenType", TYPE[extra_issue]),
                ),
            )
        )
    base = len(nodes)
    nodes += [
        CallNode(base, 0, "go:token.Payload.Valid", 0, (("tokenType", "token.TokenType", TYPE[expected]),)),
        CallNode(base + 1, 0, "go:gapi.hasPermission", 0, (("userRole", "string", ROLE[role]),)),
    ]  # fmt: skip
    branches = (BranchObs(SITE, issued != expected, base, base + 1),)
    return Execution(name, Stimulus.EXISTING_TEST, name, "passed", None, (), (), tuple(nodes), branches=branches)  # fmt: skip


RUNS = [
    _ex("t/banker", "banker", "access", "access"),
    _ex("t/wrongtype", "depositor", "refresh", "access"),
    _ex("t/depositor", "depositor", "access", "access"),
]


def _var(name: str, *sides: tuple[str, str], scope: str = "execution") -> dict[str, Any]:
    return {
        "id": f"V_{name}",
        "name": name,
        "observed_as": [
            {"at": {"entity": e, "point": p}, "kind": "identity", "scope": scope} for e, p in sides
        ],
    }


def _claim(v: dict[str, Any], runs: list[Execution]) -> tuple[str, str, int, int]:
    g = genome_from_proposals({"variables": [v]}, {}, "m")
    return identity_claim(g.variables[0], Observations(runs))


ROLE_FLOW = _var("role", ("token.CreateToken", "arg:role"), ("gapi.hasPermission", "arg:userRole"))


def test_equal_digests_across_two_entities_establish_identity() -> None:
    status, why, agree, distinct = _claim(ROLE_FLOW, RUNS)
    assert status == VERIFIED and (agree, distinct) == (3, 2), why


def test_unequal_digests_reject_identity() -> None:
    wrong = _var(
        "type", ("token.NewPayload", "arg:tokenType"), ("token.Payload.Valid", "arg:tokenType")
    )
    status, why, _, _ = _claim(wrong, RUNS)
    assert status == REJECTED and "wrongtype" in why


def test_missing_side_stays_unknown() -> None:
    missing = _var("role", ("token.CreateToken", "arg:role"), ("gapi.nobody", "arg:x"))
    status, why, _, _ = _claim(missing, RUNS)
    assert status == "" and "unknown" in why


def test_repeated_calls_with_different_values_are_ambiguous_not_verified() -> None:
    ambiguous = [_ex("t/a", "depositor", "access", "access", extra_issue="refresh"),
                 _ex("t/b", "banker", "access", "access")]  # fmt: skip
    issued = _var(
        "issued", ("token.CreateToken", "arg:tokenType"), ("token.NewPayload", "arg:tokenType")
    )
    assert (
        scoped_value(Observations(ambiguous).get("t/a"), issued["observed_as"][1])[1] == "ambiguous"
    )
    status, _, agree, _ = _claim(issued, ambiguous)
    assert status != VERIFIED and agree == 1  # only the unambiguous execution counts


def test_a_constant_without_contrast_is_not_verified() -> None:
    same = [RUNS[1], RUNS[2]]  # both depositors
    status, why, agree, distinct = _claim(ROLE_FLOW, same)
    assert (status, agree, distinct) == (SUPPORTED, 2, 1) and "no contrast" in why


def test_no_raw_value_is_exposed() -> None:
    ident = scoped_value(Observations(RUNS).get("t/banker"), ROLE_FLOW["observed_as"][0])[0]
    assert isinstance(ident, Identity) and "banker" not in repr(ident)
    g = genome_from_proposals({"variables": [ROLE_FLOW]}, {}, "m")
    assert "banker" not in dumps(g)


def _mech() -> Mechanics:
    return Mechanics(
        [{"symbol": "go:token.Payload.Valid", "file": "token/payload.go", "params": ["payload", "tokenType"],
          "sites": [{"site": SITE, "pred": "payload.Type != tokenType", "line": 3, "span": [3, 5, 3, 30],
                     "order": 0, "requires": [], "operands": [], "operand_calls": [],
                     "then_exits": True, "else_exits": False}],
          "calls": [], "stores": [], "returns": [], "unknown": []}]
    )  # fmt: skip


def _establish(tmp_path: Path, proposals: dict[str, Any], runs: list[Execution] = RUNS):  # type: ignore[no-untyped-def]
    (tmp_path / "token").mkdir(exist_ok=True)
    (tmp_path / "token/payload.go").write_text(
        'package token\n\nif payload.Type != tokenType {\nconst Access TokenType = 1\nconst Banker = "banker"\n'
    )
    sub = StateSubstrate(Substrate([], set(), tmp_path, set()), _mech(), Observations(runs))
    return establish_state(genome_from_proposals(proposals, {}, "m"), sub)


def _type_genome() -> dict[str, Any]:
    return {
        "variables": [
            _var("issued_type", ("token.CreateToken", "arg:tokenType"), ("token.NewPayload", "arg:tokenType")),
            _var("expected_type", ("token.Payload.Valid", "arg:tokenType"), scope="call"),
        ],
        "decisions": [
            {"id": "d_type", "entity": "token.Payload.Valid", "site": SITE,
             "predicate": "issued_type != expected_type",
             "true_branch": {"stops": True}, "false_branch": {},
             "evidence": [{"kind": "branch", "site": SITE, "test": "t/wrongtype", "outcome": True}]},
        ],
        "procedures": [{"id": "P", "entity": "token.Payload.Valid", "steps": ["D:d_type"],
                        "evidence": [{"kind": "source", "file": "token/payload.go", "line": 3, "text": "payload.Type"}]}],
    }  # fmt: skip


def test_identity_valued_predicate_verified_by_local_agreement(tmp_path: Path) -> None:
    g = _establish(tmp_path, _type_genome())
    issued = next(v for v in g.variables if v.name == "issued_type")
    assert (
        issued.status == VERIFIED
    )  # issued at creation == the payload's type: 3 executions, 2 values
    d = g.decisions[0]
    assert d.status == VERIFIED and "observed state" in d.status_reason, d.status_reason


def test_scenario_labels_must_follow_the_identity_pattern(tmp_path: Path) -> None:
    g = _establish(tmp_path, _type_genome())
    ob = Observations(RUNS).get("t/wrongtype")
    good = {"calls": [{"entity": "token.CreateToken", "facts": {"issued_type": "refresh"}},
                      {"entity": "token.Payload.Valid", "facts": {"expected_type": "access"}}]}  # fmt: skip
    r = compare_sequence(g, predict_sequence(g, good), ob, {SITE}, None, _skeleton(), good)
    assert r["occurrence_checks"]["contradicted"] == 0 and r["match"], r
    bad = json.loads(json.dumps(good))
    bad["calls"][1]["facts"]["expected_type"] = "refresh"  # claims equal; the digests differ
    r = compare_sequence(g, predict_sequence(g, bad), ob, {SITE}, None, _skeleton(), bad)
    assert r["occurrence_checks"]["contradicted"] == 1 and r["indeterminate"]


def _skeleton():  # type: ignore[no-untyped-def]
    from diffgenome.structure import build_skeleton

    return build_skeleton(
        RUNS, ["go:token.CreateToken", "go:token.NewPayload", "go:token.Payload.Valid"]
    )


def test_literal_identity_is_allowed_only_for_cited_source_literals(tmp_path: Path) -> None:
    access = {
        "lang": "go",
        "type": "uint8",
        "value": 1,
        "source": {"file": "token/payload.go", "line": 4},
    }
    banker = {
        "lang": "go",
        "type": "string",
        "value": "banker",
        "source": {"file": "token/payload.go", "line": 5},
    }
    assert _d(literal_canonical(access) or "") == TYPE["access"]
    assert _d(literal_canonical(banker) or "") == ROLE["banker"]
    assert literal_canonical({"lang": "go", "type": "string", "value": "x" * 65}) is None
    assert literal_canonical({"lang": "go", "type": "string", "value": 'a"b'}) is None
    _establish(tmp_path, {})  # writes the source file
    assert literal_in_source(access, tmp_path) and literal_in_source(banker, tmp_path)
    assert not literal_in_source({**banker, "value": "depositor"}, tmp_path)
    proposals = {"variables": [
        {"id": "V1", "name": "role_is_banker",
         "observed_as": {"at": {"entity": "gapi.hasPermission", "point": "arg:userRole"},
                         "kind": "equals_literal", "literal": banker}},
        {"id": "V2", "name": "role_is_depositor",  # not written in the cited source: unusable
         "observed_as": {"at": {"entity": "gapi.hasPermission", "point": "arg:userRole"},
                         "kind": "equals_literal", "literal": {**banker, "value": "depositor"}}},
    ]}  # fmt: skip
    g = _establish(tmp_path, proposals)
    assert (
        g.variables[1].status == HYPOTHESIS
        and "not an allowed literal" in g.variables[1].status_reason
    )
    from diffgenome.genome_state import _bind

    ob = Observations(RUNS).get("t/banker")
    hp = next(n for n in ob.execution.nodes if getattr(n, "symbol", "") == "go:gapi.hasPermission")
    assert _bind(g, {}, hp, "entry", ob) == {"role_is_banker": True}
    ob2 = Observations(RUNS).get("t/depositor")
    hp2 = next(
        n for n in ob2.execution.nodes if getattr(n, "symbol", "") == "go:gapi.hasPermission"
    )
    assert _bind(g, {}, hp2, "entry", ob2) == {
        "role_is_banker": False
    }  # the wrong literal is false


def test_identity_claim_is_judged_whatever_the_order_of_variables(tmp_path: Path) -> None:
    """Regression (V-F1): the identity check counted bindings through a stale loop variable
    and was skipped when the last binding checked was not an identity binding."""
    proposals = _type_genome()
    proposals["variables"].append(
        {"id": "V_lit", "name": "is_access",
         "observed_as": {"at": {"entity": "token.Payload.Valid", "point": "arg:tokenType"},
                         "kind": "equals_literal",
                         "literal": {"lang": "go", "type": "uint8", "value": 1,
                                     "source": {"file": "token/payload.go", "line": 4}}}}
    )  # fmt: skip
    g = _establish(tmp_path, proposals)
    issued = next(v for v in g.variables if v.name == "issued_type")
    assert issued.status == VERIFIED and issued.status_reason.startswith("identity verified")
