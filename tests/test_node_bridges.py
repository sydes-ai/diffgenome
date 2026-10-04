"""Experiment: an external call that re-enters repository code keeps one bridge node.

The NestJS CQRS question (domain-driven-hexagon): `commandBus.execute(command)` reaches
`DeleteUserService.execute` through `@nestjs/cqrs`, which is never instrumented, so the trace
showed the service directly under the test. With `DIFFGENOME_EXTERNAL_BRIDGES=1` a call into
a member of a non-instrumented class runs in a provisional bridge scope, and one external call
node is kept when -- and only when -- repo/test code is entered inside it. Off by default.

The "library" here is a plain JS module outside the instrumented roots, exactly the position
`node_modules` code is in.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.test_node_receiver import CHECK, COLLECTOR, TYPES, TYPESCRIPT, pytestmark  # noqa: F401

LIBRARY = """\
class ExternalThing {
  constructor() { this.handlers = new Map(); }
  register(type, handler) { this.handlers.set(type, handler); }
  dispatch(cmd) { return this.handlers.get(cmd.constructor.name).handle(cmd); }
  dispatchAll(cmds) { return cmds.map((c) => this.handlers.get(c.constructor.name).handle(c)); }
  async dispatchLater(cmd) {
    await new Promise((resolve) => setTimeout(resolve, 1));
    await null;
    return this.handlers.get(cmd.constructor.name).handle(cmd);
  }
  leaf(x) { return JSON.stringify({ x }) + Math.max(1, 2); }
}
module.exports = { ExternalThing };
"""

FIXTURE = """\
declare function require(name: string): any;
const { ExternalThing } = require("../lib/ext.js");

export class Cmd { constructor(public readonly id: string) {} }
export class Handler { handle(c: Cmd): string { return "handled:" + c.id; } }

function busWithHandler(): any {
  const bus = new ExternalThing();
  bus.register("Cmd", new Handler());
  return bus;
}
export function bridge(): string { return busWithHandler().dispatch(new Cmd("a")); }
export function two(): string[] {
  return busWithHandler().dispatchAll([new Cmd("b"), new Cmd("c")]);
}
export async function later(): Promise<string> {
  return await busWithHandler().dispatchLater(new Cmd("d"));
}
export function leaf(): string { const bus = new ExternalThing(); return bus.leaf(1); }
export function double(n: number): number { return n * 2; }
export function mapped(): number[] { return [1, 2].map(double); }
export function local(): number {
  class Local { run(): number { return 7; } }
  return new Local().run();
}
export function internal(): string { return new Handler().handle(new Cmd("e")); }
"""

RUN = r"""
const ts = require(process.argv[2]);
const fs = require("fs");
const js = ts.transpileModule(fs.readFileSync(process.argv[3], "utf8"), { compilerOptions: {
  target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
fs.writeFileSync(process.argv[4], js);
const runtime = require(process.argv[5]);
const m = require(process.argv[4]);
(async () => {
  const out = {};
  for (const name of ["bridge", "two", "later", "leaf", "mapped", "local", "internal"]) {
    runtime.begin(name);
    const result = await m[name]();
    runtime.end("passed");
    const nodes = runtime._state.nodes;
    const symbols = runtime._state.symbols;
    const label = (n) => n.symbol.replace(/^js:src\/app\./, "");
    out[name] = {
      result,
      nodes: nodes.map((n) => ({ id: n.id, parent: n.parent,
                                 sym: n.type === "call" ? label(n) : n.type,
                                 origin: n.type === "call" ? symbols.get(n.symbol).origin : null,
                                 args: n.args.map((a) => a[1]), outcome: n.outcome })),
    };
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


def _env(flag: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "DIFFGENOME_EXTERNAL_BRIDGES"}
    if flag:
        env["DIFFGENOME_EXTERNAL_BRIDGES"] = "1"
    return env


def _node(env: dict[str, str], *args: str) -> str:
    done = subprocess.run(["node", *args], capture_output=True, text=True, timeout=120, env=env)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _run(tmp_path: Path, flag: bool) -> tuple[dict, str]:
    (tmp_path / "src").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "types").mkdir()
    (tmp_path / "lib" / "ext.js").write_text(LIBRARY)
    app = tmp_path / "src" / "app.ts"
    app.write_text(FIXTURE)
    (tmp_path / "types" / "globals.d.ts").write_text(TYPES)
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "run.js").write_text(RUN)
    _node(
        _env(flag),
        str(COLLECTOR / "instrument.js"),
        "--root",
        str(tmp_path),
        "--src",
        "src",
        "--runtime",
        str(COLLECTOR / "runtime.js"),
    )
    text = app.read_text()
    out = json.loads(
        _node(
            _env(flag),
            str(tmp_path / "run.js"),
            str(TYPESCRIPT),
            str(app),
            str(tmp_path / "src" / "app.js"),
            str(COLLECTOR / "runtime.js"),
        )
    )
    diagnostics = json.loads(
        _node(
            _env(flag),
            str(tmp_path / "check.js"),
            str(TYPESCRIPT),
            str(app),
            str(tmp_path / "types" / "globals.d.ts"),
        )
    )
    assert diagnostics == [], diagnostics
    return out, text


def _external(trace: dict) -> list[dict]:
    return [n for n in trace["nodes"] if n["origin"] == "external"]


def _by_id(trace: dict) -> dict[int, dict]:
    return {n["id"]: n for n in trace["nodes"]}


def test_a_bridge_keeps_one_external_node_between_caller_and_handler(tmp_path: Path) -> None:
    out, _ = _run(tmp_path, flag=True)
    trace = out["bridge"]
    assert trace["result"] == "handled:a"
    [bridge] = _external(trace)
    nodes = _by_id(trace)
    assert bridge["sym"] == "js:external:ExternalThing.dispatch"
    assert bridge["args"] == ["Cmd"] and bridge["outcome"] == "returned"
    assert nodes[bridge["parent"]]["sym"] == "bridge"  # the repo frame that called out
    handler = next(n for n in trace["nodes"] if n["sym"] == "Handler.handle")
    assert handler["parent"] == bridge["id"]  # the repo code it reached hangs under it
    # several repo entries under one external invocation share one bridge node
    two = out["two"]
    [shared] = _external(two)
    assert shared["sym"] == "js:external:ExternalThing.dispatchAll"
    assert [n["parent"] for n in two["nodes"] if n["sym"] == "Handler.handle"] == [shared["id"]] * 2


def test_b_an_external_leaf_call_leaves_no_bridge(tmp_path: Path) -> None:
    out, _ = _run(tmp_path, flag=True)
    assert out["leaf"]["result"] == '{"x":1}2'
    assert _external(out["leaf"]) == []
    # nor does a call into this repository's own classes, including a local class that
    # registerClass never sees (marked from inside its own body)
    assert _external(out["internal"]) == []
    assert _external(out["local"]) == [] and out["local"]["result"] == 7


def test_c_a_callback_through_an_external_function_is_also_a_bridge(tmp_path: Path) -> None:
    """Not classified yet: `[1, 2].map(double)` is reported as a bridge like any other."""
    out, _ = _run(tmp_path, flag=True)
    trace = out["mapped"]
    assert trace["result"] == [2, 4]
    [bridge] = _external(trace)
    assert bridge["sym"] == "js:external:Array.map"
    assert [n["parent"] for n in trace["nodes"] if n["sym"] == "double"] == [bridge["id"]] * 2


def test_d_the_bridge_survives_awaits_inside_the_external_code(tmp_path: Path) -> None:
    out, _ = _run(tmp_path, flag=True)
    trace = out["later"]
    assert trace["result"] == "handled:d"
    [bridge] = _external(trace)
    assert bridge["sym"] == "js:external:ExternalThing.dispatchLater"
    assert bridge["outcome"] == "returned"
    handler = next(n for n in trace["nodes"] if n["sym"] == "Handler.handle")
    assert handler["parent"] == bridge["id"]


def test_off_by_default(tmp_path: Path) -> None:
    out, text = _run(tmp_path, flag=False)
    assert "markClass" not in text
    assert all(_external(trace) == [] for trace in out.values())
    handler = next(n for n in out["bridge"]["nodes"] if n["sym"] == "Handler.handle")
    assert _by_id(out["bridge"])[handler["parent"]]["sym"] == "bridge"  # today's collapse
