"""JSON encoding of the event protocol. One `Execution` per document; deterministic output."""

from __future__ import annotations

import dataclasses
import json
from enum import Enum
from typing import Any

from diffgenome.model import (
    CallNode,
    Collector,
    Execution,
    Fidelity,
    Node,
    Origin,
    OsEventKind,
    OsEventNode,
    Plane,
    SourceLocation,
    Stimulus,
    SubstitutionMechanism,
    SubstitutionNode,
    Symbol,
)

_NODE_TYPES: dict[str, type[Node]] = {
    "call": CallNode,
    "substitution": SubstitutionNode,
    "os_event": OsEventNode,
}
_TYPE_NAMES: dict[type, str] = {cls: name for name, cls in _NODE_TYPES.items()}


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {f.name: _encode(getattr(value, f.name)) for f in dataclasses.fields(value)}
        node_type = _TYPE_NAMES.get(type(value))
        return {"type": node_type, **out} if node_type else out
    if isinstance(value, tuple | list):
        return [_encode(v) for v in value]
    return value


def execution_to_json(execution: Execution) -> str:
    return json.dumps(_encode(execution), indent=1, sort_keys=False) + "\n"


def _node_from_dict(d: dict[str, Any]) -> Node:
    d = dict(d)
    cls = _NODE_TYPES[d.pop("type")]
    if "args" in d:
        d["args"] = tuple((n, sh, dg) for n, sh, dg in d["args"])
    if cls is SubstitutionNode:
        d["mechanism"] = SubstitutionMechanism(d["mechanism"])
        d["path"] = tuple(d["path"])
    elif cls is OsEventNode:
        d["kind"] = OsEventKind(d["kind"])
    return cls(**d)


def execution_from_json(text: str) -> Execution:
    d = json.loads(text)
    return Execution(
        id=d["id"],
        stimulus=Stimulus(d["stimulus"]),
        stimulus_ref=d["stimulus_ref"],
        outcome=d["outcome"],
        revision=d["revision"],
        collectors=tuple(
            Collector(c["name"], Plane(c["plane"]), Fidelity(c["fidelity"]))
            for c in d["collectors"]
        ),
        symbols=tuple(
            Symbol(
                s["id"],
                Origin(s["origin"]),
                SourceLocation(**s["location"]) if s["location"] else None,
            )
            for s in d["symbols"]
        ),
        nodes=tuple(_node_from_dict(n) for n in d["nodes"]),
    )
