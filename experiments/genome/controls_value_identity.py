"""Value-identity controls (docs/design-value-identity.md), seeded into the fresh v5
proposals of Case B (RBAC) and Case C (token type).

i1 wrong equality          an identity claim across boundaries whose shown digests differ
i2 swapped identity        the issued type taken from another occurrence (the verification's
                           expected type) instead of the creation
i3 overgeneralized constant every shown scenario claims the expected type is access
i4 missing side            an identity claim whose second side names a boundary never observed
i5 wrong literal           a literal binding pointed at the other source literal

usage: controls_value_identity.py <B|C> <case-dir>
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


def var(p: dict[str, Any], name: str) -> dict[str, Any]:
    return next(v for v in p["variables"] if v["name"] == name)


def main() -> int:
    case, d = sys.argv[1], Path(sys.argv[2])
    base = json.loads((d / "proposals.json").read_text())
    hold = json.loads((d / "holdout.json").read_text())
    out = d / "controls"
    out.mkdir(exist_ok=True)
    controls: dict[str, Any] = {}
    if case == "C":
        c = copy.deepcopy(
            base
        )  # i1: issued == expected as one identity (differs in wrong-type tests)
        c["variables"].append(
            {
                "id": "V_i1",
                "name": "type_everywhere",
                "evidence": [],
                "observed_as": [
                    {
                        "at": {"entity": "token.NewPayload", "point": "arg:tokenType"},
                        "kind": "identity",
                        "scope": "execution",
                    },
                    {
                        "at": {"entity": "token.Payload.Valid", "point": "arg:tokenType"},
                        "kind": "identity",
                        "scope": "execution",
                    },
                ],
            }
        )
        controls["i1-wrong-equality"] = c
        c = copy.deepcopy(base)  # i2: issued type bound to the verification's expected type
        var(c, "issued_type")["observed_as"] = [
            {
                "at": {"entity": "token.PasetoMaker.VerifyToken", "point": "arg:tokenType"},
                "kind": "identity",
                "scope": "execution",
            }
        ]
        controls["i2-swapped-identity"] = c
        c = copy.deepcopy(base)  # i3: every shown scenario says the expected type is access
        for t in hold["shown"]:
            for call in c["scenarios"][t]["calls"]:
                if (
                    "expected_is_access" in (call.get("facts") or {})
                    or call["entity"].endswith("Payload.Valid")
                    or call["entity"].endswith("VerifyToken")
                ):
                    call.setdefault("facts", {})["expected_is_access"] = True
        controls["i3-overgeneralized-constant"] = c
        c = copy.deepcopy(base)  # i4: second side never observed
        v = var(c, "expected_type")
        v["observed_as"] = [
            v["observed_as"][0],
            {
                "at": {"entity": "token.NoSuchMaker.VerifyToken", "point": "arg:tokenType"},
                "kind": "identity",
            },
        ]
        controls["i4-missing-side"] = c
        c = copy.deepcopy(base)  # i5: "is access" pointed at the refresh literal
        b = var(c, "expected_is_access")["observed_as"]
        b = b[0] if isinstance(b, list) else b
        refresh = var(base, "expected_is_refresh")["observed_as"]
        refresh = refresh[0] if isinstance(refresh, list) else refresh
        b["literal"] = copy.deepcopy(refresh["literal"])
        controls["i5-wrong-literal"] = c
    else:
        c = copy.deepcopy(base)  # i1: the token's username is the role later checked
        c["variables"].append(
            {
                "id": "V_i1",
                "name": "name_is_role",
                "evidence": [],
                "observed_as": [
                    {
                        "at": {"entity": "token.PasetoMaker.CreateToken", "point": "arg:username"},
                        "kind": "identity",
                        "scope": "execution",
                    },
                    {
                        "at": {"entity": "gapi.hasPermission", "point": "arg:userRole"},
                        "kind": "identity",
                        "scope": "execution",
                    },
                ],
            }
        )
        controls["i1-wrong-equality"] = c
        c = copy.deepcopy(base)  # i4: second side of the username identity never observed
        v = var(c, "token_username")
        v["observed_as"] = [
            v["observed_as"][0],
            {
                "at": {"entity": "token.NoSuchMaker.CreateToken", "point": "arg:username"},
                "kind": "identity",
                "scope": "execution",
            },
        ]
        controls["i4-missing-side"] = c
        c = copy.deepcopy(base)  # i5: "caller is banker" pointed at the depositor literal
        b = var(c, "caller_is_banker")["observed_as"]
        b = b[0] if isinstance(b, list) else b
        b["literal"] = {
            **b["literal"],
            "value": "depositor",
            "source": {**b["literal"]["source"], "line": 4},
        }
        controls["i5-wrong-literal"] = c
    for k, v in controls.items():
        (out / f"{k}.proposals.json").write_text(json.dumps(v, indent=1) + "\n")
    print(" ".join(controls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
