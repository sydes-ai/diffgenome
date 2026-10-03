"""Constructor instrumentation must keep a derived class's `super(...)` a root-level statement.

Seen on domain-driven-hexagon: every constructor body was wrapped in `try { ... } finally`,
so `super(pool, mapper, ...)` in `UserRepository` (a derived class with initialized fields)
became nested and TypeScript rejected it with TS2401 before any test ran. The statements up
to and including the root-level `super(...)` now stay at the root, entry is recorded once it
returns, and only the rest is wrapped.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.test_node_receiver import CHECK, COLLECTOR, TYPES, TYPESCRIPT, _node, pytestmark  # noqa: F401

FIXTURE = """\
export class Base {
  protected tag = "base";
  constructor(public readonly name: string) {
    if (!name) throw new Error("no name");
    this.tag = this.tag + ":" + name;
  }
  get label(): string { return this.tag; }
}

export class Derived extends Base {
  #secret = 41;
  count = 1;
  constructor(name: string, private readonly extra: number, early = false) {
    const upper = name.toUpperCase();
    super(upper);
    this.count += extra;
    if (early) return;
    this.#secret += 1;
    if (extra < 0) throw new RangeError("negative");
  }
  get secret(): number { return this.#secret; }
  get total(): number { return this.count + this.extra; }
}

export class Conditional extends Base {
  constructor(flag: boolean) {
    if (flag) { super("yes"); } else { super("no"); }
  }
}

export class Implicit extends Base {}

export class FailingSuper extends Base {
  x = 1;
  constructor() { super(""); }
}

export function probe(): number { return 1; }
"""

RUN = r"""
const ts = require(process.argv[2]);
const fs = require("fs");
const js = ts.transpileModule(fs.readFileSync(process.argv[3], "utf8"), { compilerOptions: {
  target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
fs.writeFileSync(process.argv[4], js);
const runtime = require(process.argv[5]);
const m = require(process.argv[4]);
const caught = (fn) => { try { fn(); return null; } catch (e) { return e.constructor.name + ":" + e.message; } };
runtime.begin("t");
const d = new m.Derived("ab", 2);
const early = new m.Derived("cd", 1, true);
const r = {
  derived: [d.name, d.label, d.count, d.secret, d.total],
  early: [early.name, early.count, early.secret],
  throwsAfterSuper: caught(() => new m.Derived("ef", -1)),
  conditional: [new m.Conditional(true).name, new m.Conditional(false).name],
  implicit: new m.Implicit("z").label,
  failingSuper: caught(() => new m.FailingSuper()),
  probe: m.probe(),
};
const nodes = runtime._state.nodes.filter((n) => n.type === "call")
  .map((n) => ({ sym: n.symbol.replace(/^js:src\/app\./, ""), parent: n.parent, outcome: n.outcome }));
process.stdout.write(JSON.stringify({ results: r, nodes }));
"""


def _instrument(tmp_path: Path) -> dict[str, Path]:
    (tmp_path / "src").mkdir()
    (tmp_path / "types").mkdir()
    app = tmp_path / "src" / "app.ts"
    app.write_text(FIXTURE)
    (tmp_path / "types" / "original.ts").write_text(FIXTURE)
    (tmp_path / "types" / "globals.d.ts").write_text(TYPES)
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "run.js").write_text(RUN)
    subprocess.run(
        ["node", str(COLLECTOR / "instrument.js"), "--root", str(tmp_path), "--src", "src",
         "--runtime", str(COLLECTOR / "runtime.js")],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return {"root": tmp_path, "app": app}


def _diagnostics(root: Path, file: Path) -> list[dict]:
    return json.loads(_node(root / "check.js", str(TYPESCRIPT), str(file), str(root / "types" / "globals.d.ts")))


def test_derived_constructors_type_check_after_instrumentation(tmp_path: Path) -> None:
    paths = _instrument(tmp_path)
    assert _diagnostics(tmp_path, tmp_path / "types" / "original.ts") == []  # the fixture is clean
    assert _diagnostics(tmp_path, paths["app"]) == []  # no TS2401


def test_super_stays_a_root_level_statement_and_entry_follows_it(tmp_path: Path) -> None:
    text = _instrument(tmp_path)["app"].read_text()
    derived = text[text.index("class Derived"):text.index("class Conditional")]
    body = derived[derived.index("constructor("):]
    # the pre-super statement, then super, then entry, then the wrapped remainder
    assert body.index("toUpperCase") < body.index("super(") < body.index("__dg.enter(") < body.index("try {")
    assert "this" not in body[:body.index("__dg.enter(")].split("{", 1)[1].split("super(")[0]
    # a derived constructor without a root-level super keeps the whole-body wrap
    conditional = text[text.index("class Conditional"):text.index("class Implicit")]
    assert conditional.index("__dg.enter(") < conditional.index("try {") < conditional.index("super(")


def test_constructor_semantics_and_outcomes_are_preserved(tmp_path: Path) -> None:
    paths = _instrument(tmp_path)
    out = json.loads(_node(tmp_path / "run.js", str(TYPESCRIPT), str(paths["app"]),
                           str(tmp_path / "app.js"), str(COLLECTOR / "runtime.js")))
    assert out["results"] == {
        "derived": ["AB", "base:AB", 3, 42, 5],
        "early": ["CD", 2, 41],
        "throwsAfterSuper": "RangeError:negative",
        "conditional": ["yes", "no"],
        "implicit": "base:z",
        "failingSuper": "Error:no name",
        "probe": 1,
    }
    nodes = out["nodes"]
    derived = [n for n in nodes if n["sym"] == "Derived.constructor"]
    assert [n["outcome"] for n in derived] == ["returned", "returned", "raised:js:RangeError"]
    # a super() that throws leaves no half-entered constructor behind: the next call is
    # attributed to the stimulus root, not to a constructor that never completed
    assert not any(n["sym"] == "FailingSuper.constructor" for n in nodes)
    assert [n["parent"] for n in nodes if n["sym"] == "probe"] == [0]
