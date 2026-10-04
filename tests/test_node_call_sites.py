"""Call-site instrumentation must not change what TypeScript sees at the call.

Seen on domain-driven-hexagon: `if (Array.isArray(value)) { value.length ... }` in
`src/libs/guard.ts` was rewritten to `if (__dg.callm(Array, "isArray", [value]))`, whose
result is `any`, so the `value is any[]` predicate no longer narrowed `value` and type
checking failed (TS18048, TS2339) before any test ran. The same rewrite lost user-defined
predicates, assertion functions, overload selection and contextual typing of arguments.

Calls are now instrumented at the callee through helpers typed as identities, and a call
statement through a plain or dotted name (where an assertion function narrows) is left as
written and observed from either side. A Jest mock is still recorded as a stand-in.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from tests.test_node_receiver import (  # noqa: F401
    CHECK,
    COLLECTOR,
    TYPES,
    TYPESCRIPT,
    _node,
    pytestmark,
)

FIXTURE = """\
interface Foo { foo: number }

export function isFoo(x: unknown): x is Foo {
  return typeof x === "object" && x !== null && "foo" in x;
}
export function assertFoo(x: unknown): asserts x is Foo {
  if (!isFoo(x)) throw new TypeError("not a Foo");
}
export function pick(x: string): string;
export function pick(x: number): number;
export function pick(x: string | number): string | number { return x; }

export class Checks {
  static isFoo(x: unknown): x is Foo { return isFoo(x); }
  static assertFoo(x: unknown): asserts x is Foo { assertFoo(x); }
}

export function lengthOf(value: unknown): number {
  if (Array.isArray(value)) {
    return value.length;
  }
  return -1;
}
export function fooOf(value: unknown): number {
  if (isFoo(value)) return value.foo;
  if (Checks.isFoo(value)) return value.foo;
  return -1;
}
export function asserted(value: unknown): number {
  assertFoo(value);
  return value.foo;
}
export function assertedViaClass(value: unknown): number {
  Checks.assertFoo(value);
  return value.foo;
}
export function overloaded(): string {
  return pick("ab").toUpperCase() + pick(2).toFixed(1);
}
export function contextual(xs: number[]): number[] {
  return xs.map((x) => x * 2).filter((x) => x > 2);
}

export interface Notifier { notify(msg: string): number }
export function useNotifier(n: Notifier, cb: (s: string) => number): number {
  n.notify("statement");
  const r = n.notify("expression");
  return r + cb("fn");
}
"""

RUN = r"""
const ts = require(process.argv[2]);
const fs = require("fs");
const js = ts.transpileModule(fs.readFileSync(process.argv[3], "utf8"), { compilerOptions: {
  target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
fs.writeFileSync(process.argv[4], js);
const runtime = require(process.argv[5]);
const m = require(process.argv[4]);

// A Jest-shaped mock: what the runtime recognizes, and the record Jest keeps of each call.
function mockFn(impl) {
  const fn = function (...args) {
    fn.mock.calls.push(args);
    const i = fn.mock.results.push({ type: "incomplete", value: undefined }) - 1;
    try {
      const v = impl.apply(this, args);
      fn.mock.results[i] = { type: "return", value: v };
      return v;
    }
    catch (e) { fn.mock.results[i] = { type: "throw", value: e }; throw e; }
  };
  fn._isMockFunction = true;
  fn.mock = { calls: [], results: [] };
  fn.getMockName = () => "jest.fn()";
  return fn;
}
const caught = (fn) => {
  try { return fn(); } catch (e) { return e.constructor.name + ":" + e.message; }
};

runtime.begin("t");
const results = {
  lengthOf: [m.lengthOf([1, 2, 3]), m.lengthOf("abc")],
  fooOf: [m.fooOf({ foo: 4 }), m.fooOf(1)],
  asserted: [m.asserted({ foo: 5 }), caught(() => m.asserted(2))],
  assertedViaClass: m.assertedViaClass({ foo: 6 }),
  overloaded: m.overloaded(),
  contextual: m.contextual([1, 2, 3]),
  notifier: m.useNotifier({ notify: mockFn((s) => s.length) }, mockFn(() => 10)),
  throwingStatement: caught(() => m.useNotifier(
    { notify: mockFn(() => { throw new RangeError("down"); }) }, mockFn(() => 0))),
};
runtime.end("passed");
const nodes = runtime._state.nodes.map((n) => ({
  id: n.id, type: n.type, parent: n.parent, sym: (n.symbol || "").replace(/^js:src\/app\./, ""),
  mechanism: n.mechanism, substitute: n.substitute, args: n.args, outcome: n.outcome,
}));
process.stdout.write(JSON.stringify({ results, nodes }));
"""


def _instrument(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "types").mkdir()
    app = tmp_path / "src" / "app.ts"
    app.write_text(FIXTURE)
    (tmp_path / "types" / "original.ts").write_text(FIXTURE)
    (tmp_path / "types" / "globals.d.ts").write_text(TYPES)
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "run.js").write_text(RUN)
    subprocess.run(
        [
            "node",
            str(COLLECTOR / "instrument.js"),
            "--root",
            str(tmp_path),
            "--src",
            "src",
            "--runtime",
            str(COLLECTOR / "runtime.js"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return app


def _diagnostics(root: Path, file: Path) -> list[str]:
    out = json.loads(
        _node(root / "check.js", str(TYPESCRIPT), str(file), str(root / "types" / "globals.d.ts"))
    )
    return [f"TS{d['code']}: {d['message']}" for d in out]


def test_instrumented_calls_keep_their_static_types(tmp_path: Path) -> None:
    """Predicates (built-in, user-defined, static), assertion functions, overloads and
    contextual typing all survive: the instrumented file type-checks under `strict`."""
    app = _instrument(tmp_path)
    assert _diagnostics(tmp_path, tmp_path / "types" / "original.ts") == []  # the fixture is clean
    assert _diagnostics(tmp_path, app) == []


def test_call_shapes_leave_the_original_call_visible(tmp_path: Path) -> None:
    text = _instrument(tmp_path).read_text()
    assert "callm" not in text and "callf" not in text  # no call routed through an `any` helper
    assert '__dg.m(Array, "isArray").isArray(value)' in text
    assert "__dg.f(isFoo)(value)" in text
    # an assertion statement is left exactly as written, observed from either side
    for target in ("assertFoo", "Checks.assertFoo"):
        name = re.escape(target)
        assert re.search(
            rf"const (__dgt_\d+) = __dg\.pre\({name}\);\s+{name}\(value\);\s+__dg\.post\(\1\);",
            text,
        )


def test_runtime_behaviour_and_call_evidence_are_preserved(tmp_path: Path) -> None:
    app = _instrument(tmp_path)
    out = json.loads(
        _node(
            tmp_path / "run.js",
            str(TYPESCRIPT),
            str(app),
            str(tmp_path / "app.js"),
            str(COLLECTOR / "runtime.js"),
        )
    )
    assert out["results"] == {
        "lengthOf": [3, -1],
        "fooOf": [4, -1],
        "asserted": [5, "TypeError:not a Foo"],
        "assertedViaClass": 6,
        "overloaded": "AB2.0",
        "contextual": [4, 6],
        "notifier": 20,
        "throwingStatement": "RangeError:down",
    }
    nodes = out["nodes"]
    by_id = {n["id"]: n for n in nodes}
    calls = [n for n in nodes if n["type"] == "call"]

    # ordinary calls still nest under their caller
    def parent_sym(sym: str) -> set[str]:
        return {
            by_id[n["parent"]]["sym"] for n in calls if n["sym"] == sym and n["parent"] in by_id
        }

    assert parent_sym("isFoo") >= {"fooOf", "assertFoo", "Checks.isFoo"}
    assert parent_sym("assertFoo") >= {"asserted", "Checks.assertFoo"}
    assert parent_sym("pick") == {"overloaded"}

    # mocks are still recorded as stand-ins, from every call shape, with args and outcome
    stand_ins = [n for n in nodes if n["type"] == "substitution"]
    assert all(
        n["mechanism"] == "mock_object" and n["substitute"] == "js:jest.fn" for n in stand_ins
    )
    first = [n for n in stand_ins if by_id[n["parent"]]["sym"] == "useNotifier"]
    # statement notify (pre/post), expression notify (m), cb (f); then the throwing statement
    assert [n["outcome"].split(":")[0] for n in first] == [
        "returned",
        "returned",
        "returned",
        "raised",
    ]
    assert first[3]["outcome"] == "raised:js:RangeError"
    assert all(n["args"] for n in first)  # argument shapes recorded for each
