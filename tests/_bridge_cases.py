"""Shared inputs for the external-bridge evidence tests.

`legacy_outputs()` renders the runtime contract and the graph for executions that contain no
external bridge. Its result was captured once, before bridge evidence existed, as
`fixtures/bridges/legacy-*.json`; the tests require it to stay byte-identical.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from diffgenome.change import ChangedRange, ChangeSet
from diffgenome.compose import build_corpus
from diffgenome.graph import build_graph
from diffgenome.model import Execution
from diffgenome.runtime_evidence import build_runtime_evidence
from diffgenome.serialize import execution_from_json
from tests.test_runtime_evidence import MECH, _change, _ex, _Index

FIXTURES = Path(__file__).parent / "fixtures" / "bridges"

SERVICE = "js:src/modules/user/commands/delete-user/delete-user.service.DeleteUserService.execute"
SERVICE_FILE = "src/modules/user/commands/delete-user/delete-user.service.ts"
TEST_FRAME = "js:tests/diffgenome-cqrs.e2e-spec.<anon>@9.<anon>@13"


@dataclass
class _Def:
    symbol: str
    path: str
    start: int
    end: int
    kind: str


class CqrsIndex:
    """The definitions the CQRS traces need (what a SymbolIndex would find)."""

    defs: ClassVar[dict[str, _Def]] = {
        SERVICE: _Def(SERVICE, SERVICE_FILE, 25, 37, "function"),
        TEST_FRAME: _Def(TEST_FRAME, "tests/diffgenome-cqrs.e2e-spec.ts", 13, 27, "function"),
    }

    def find(self, s: str) -> _Def | None:
        return self.defs.get(s)

    def is_test(self, s: str) -> bool:
        return s.startswith("js:tests/")


def cqrs_change() -> ChangeSet:
    return ChangeSet("cqrs", [ChangedRange(SERVICE_FILE, frozenset({30}))], [SERVICE], [])


def trace(name: str) -> Execution:
    return execution_from_json((FIXTURES / f"{name}.trace.json").read_text())


def contract(executions: list[Execution], change: ChangeSet, index: object, mech: list) -> dict:
    return build_runtime_evidence(executions, change, index, mech, [], test_scope="tests/")


def graph_json(executions: list[Execution]) -> dict:
    return build_graph(build_corpus(executions)).to_json()


def legacy_outputs() -> dict[str, str]:
    """Bridge-free inputs: the existing synthetic Python executions and the real CQRS
    trace recorded with DIFFGENOME_EXTERNAL_BRIDGES off."""
    py = [_ex("t::a", "returned", True, False), _ex("t::b", "raised:py:ValueError", True, True)]
    cqrs = [trace("cqrs-flag-off")]
    return {
        "legacy-python-contract": json.dumps(contract(py, _change(), _Index(), MECH), indent=1),
        "legacy-python-graph": json.dumps(graph_json(py), indent=1),
        "legacy-cqrs-contract": json.dumps(
            contract(cqrs, cqrs_change(), CqrsIndex(), []), indent=1
        ),
        "legacy-cqrs-graph": json.dumps(graph_json(cqrs), indent=1),
    }
