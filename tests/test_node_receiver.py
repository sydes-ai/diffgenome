"""The receiver the Node instrumenter reports must never be a bare `this` in a free function.

Seen on domain-driven-hexagon (NestJS, ts-jest): top-level helpers such as
`export async function generateTestingApplication()` and `export function getTestServer()`
were rewritten to `__dg.run(..., this, ...)` / `__dg.enter(..., this)`, and type checking
rejected every one with TS2683 ("'this' implicitly has type 'any'") before any test ran.

These tests instrument a fixture covering each function form, type-check the result under
`strict` (which includes `noImplicitThis`, the setting ts-jest enforced there), and execute
it to show `this` semantics and receiver capture are unchanged where a receiver exists.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

import diffgenome

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="no Node.js")

COLLECTOR = Path(diffgenome.__file__).parent / "_collectors" / "node"
TYPESCRIPT = COLLECTOR / "node_modules" / "typescript"

FIXTURE = """\
export async function generateTestingApplication(): Promise<number> { return 1; }
export function getTestServer(): number { return 2; }
export function* counter(): Generator<number> { yield 1; yield 2; }
export const addOne = async (x: number): Promise<number> => x + 1;
export function outer(): number {
  function inner(): number { return 3; }
  const viaArrow = (): number => inner();
  return viaArrow();
}

export class Repo {
  private n = 1;
  constructor(public readonly k: number) {}
  get size(): number { return this.n; }
  set size(v: number) { this.n = v; }
  find(id: number): number { return id + this.n; }
  async load(): Promise<number> { return this.n; }
  *ids(): Generator<number> { yield this.n; }
  static make(): Repo { return new Repo(7); }
}

export const obj = {
  v: 2,
  m(): number { return this.v; },
  fe: function (): number { return this.v; },
};

export function withThis(this: { v: number }, a: number): number { return this.v + a; }
export function* genThis(this: { v: number }): Generator<number> { yield this.v; }
export async function asyncThis(this: { v: number }): Promise<number> { return this.v; }
"""

TYPES = "declare function require(name: string): any;\n"

CHECK = """\
const ts = require(process.argv[2]);
const files = process.argv.slice(3);
const program = ts.createProgram(files, {
  strict: true, noEmit: true, target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS,
});
const out = ts.getPreEmitDiagnostics(program).map((d) => ({
  code: d.code, message: ts.flattenDiagnosticMessageText(d.messageText, " "),
}));
process.stdout.write(JSON.stringify(out));
"""

RUN = r"""
const ts = require(process.argv[2]);
const fs = require("fs");
const src = fs.readFileSync(process.argv[3], "utf8");
const js = ts.transpileModule(src, { compilerOptions: {
  target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
fs.writeFileSync(process.argv[4], js);
const runtime = require(process.argv[5]);
const m = require(process.argv[4]);
(async () => {
  runtime.begin("t");
  const repo = new m.Repo(1);
  repo.size = 4;
  const r = {
    app: await m.generateTestingApplication(), server: m.getTestServer(), counter: [...m.counter()],
    addOne: await m.addOne(1), outer: m.outer(), find: repo.find(1), size: repo.size,
    load: await repo.load(), ids: [...repo.ids()], make: m.Repo.make().k,
    objM: m.obj.m(), objFe: m.obj.fe(), withThis: m.withThis.call({ v: 5 }, 1),
    genThis: [...m.genThis.call({ v: 9 })], asyncThis: await m.asyncThis.call({ v: 3 }),
  };
  const facts = {};
  for (const n of runtime._state.nodes) {
    if (n.type === "call") facts[n.symbol.replace(/^js:src\//, "")] = n.state.map((s) => s[0]);
  }
  process.stdout.write(JSON.stringify({ results: r, facts }));
})();
"""


def _node(script: Path, *args: str) -> str:
    done = subprocess.run(["node", str(script), *args], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture()
def instrumented(tmp_path: Path) -> dict[str, Path]:
    (tmp_path / "src").mkdir()
    (tmp_path / "types").mkdir()
    app = tmp_path / "src" / "app.ts"
    app.write_text(FIXTURE)
    original = tmp_path / "types" / "original.ts"
    original.write_text(FIXTURE)
    (tmp_path / "types" / "globals.d.ts").write_text(TYPES)
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "run.js").write_text(RUN)
    subprocess.run(
        ["node", str(COLLECTOR / "instrument.js"), "--root", str(tmp_path), "--src", "src",
         "--runtime", str(COLLECTOR / "runtime.js"), "--index", str(tmp_path / "index.json")],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return {"root": tmp_path, "app": app, "original": original,
            "globals": tmp_path / "types" / "globals.d.ts"}


def _diagnostics(paths: dict[str, Path], file: Path) -> list[dict]:
    return json.loads(_node(paths["root"] / "check.js", str(TYPESCRIPT), str(file), str(paths["globals"])))


def test_the_check_reproduces_the_failure_class(instrumented: dict[str, Path]) -> None:
    """Control: a bare `this` handed out of a free function is TS2683 under this config."""
    bad = instrumented["root"] / "types" / "bad.ts"
    bad.write_text("declare const __dg: any;\nexport function getTestServer(): number { return __dg.enter({}, [], this); }\n")
    assert [d["code"] for d in _diagnostics(instrumented, bad)] == [2683]


def test_instrumented_output_type_checks_under_strict(instrumented: dict[str, Path]) -> None:
    assert _diagnostics(instrumented, instrumented["original"]) == []  # the fixture itself is clean
    assert _diagnostics(instrumented, instrumented["app"]) == []


def test_free_functions_report_no_receiver_and_methods_report_theirs(instrumented: dict[str, Path]) -> None:
    text = instrumented["app"].read_text()

    def receiver_of(name: str) -> str:
        start = text.index(name)
        call = min(i for i in (text.find("__dg.enter(", start), text.find("__dg.run(", start)) if i >= 0)
        depth, i = 0, text.index("(", call)
        args, current = [], ""
        for ch in text[i + 1:]:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    args.append(current.strip())
                    break
                depth -= 1
            if ch == "," and depth == 0:
                args.append(current.strip())
                current = ""
                continue
            current += ch
        return args[2]

    for free in ("function generateTestingApplication", "function getTestServer", "function* counter",
                 "function outer", "function inner", "addOne ="):
        assert receiver_of(free) == "undefined", free
    for bound in ("get size", "set size", "find(id", "async load", "*ids", "static make", "m()",
                  "fe: function", "function withThis", "function* genThis", "function asyncThis"):
        assert receiver_of(bound) == "this", bound
    # a `this` parameter is a type annotation, not an argument
    assert '"params": ["a"]' in text or "params: [\"a\"]" in text


def test_semantics_and_receiver_capture_are_preserved(instrumented: dict[str, Path]) -> None:
    root = instrumented["root"]
    out = json.loads(_node(root / "run.js", str(TYPESCRIPT), str(instrumented["app"]),
                           str(root / "app.js"), str(COLLECTOR / "runtime.js")))
    assert out["results"] == {
        "app": 1, "server": 2, "counter": [1, 2], "addOne": 2, "outer": 3, "find": 5, "size": 4,
        "load": 4, "ids": [4], "make": 7, "objM": 2, "objFe": 2, "withThis": 6, "genThis": [9],
        "asyncThis": 3,
    }
    facts = out["facts"]
    # instance members still report the receiver's state
    assert "self:type" in facts["app.Repo.find"] and "self.n" in facts["app.Repo.find"]
    assert "self:type" in facts["app.Repo.ids"]
    # free functions have no receiver state to report
    assert facts["app.getTestServer"] == []
    assert facts["app.generateTestingApplication"] == []


def test_javascript_files_get_no_type_annotations(tmp_path: Path) -> None:
    """The same rewrite applies to .js sources, which cannot carry `: any` or `this:`."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lib.js").write_text(
        "function* free() { yield 1; }\n"
        "const o = { v: 3, *g() { yield this.v; }, async a() { return this.v; } };\n"
        "module.exports = { free, o };\n"
    )
    subprocess.run(
        ["node", str(COLLECTOR / "instrument.js"), "--root", str(tmp_path), "--src", "src",
         "--runtime", str(COLLECTOR / "runtime.js")],
        check=True, capture_output=True, text=True, timeout=120,
    )
    text = (tmp_path / "src" / "lib.js").read_text()
    assert ": any" not in text and "this:" not in text
    probe = tmp_path / "probe.js"
    probe.write_text(
        f"const m = require({json.dumps(str(tmp_path / 'src' / 'lib.js'))});\n"
        "m.o.a().then((a) => process.stdout.write(JSON.stringify([[...m.free()], [...m.o.g()], a])));\n"
    )
    assert json.loads(_node(probe)) == [[1], [3], 3]
