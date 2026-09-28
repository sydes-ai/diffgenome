"""Node/TypeScript runtime adapter: source instrumentation + Jest.

Everything Node-specific lives here and in tools/node-collector. The workspace copy is
instrumented in place by `instrument.js` (our tool, our pinned TypeScript; no target code
runs), a workspace-only Jest config loads `jest-setup.js`, and the instrumented tests run
inside the sandbox with loopback allowed (test servers bind localhost; that is not egress).
The symbol index comes from the instrumenter's definition list, so diff lines map to the
same identities the collector emits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from diffgenome.model import Execution, Stimulus, SymbolId
from diffgenome.probe import copy_probe_traces
from diffgenome.runtime import SymbolIndex
from diffgenome.sandbox import Workspace
from diffgenome.serialize import execution_from_json

TOOLS = Path(__file__).resolve().parents[3] / "tools" / "node-collector"


@dataclass(frozen=True)
class Definition:
    symbol: SymbolId
    path: str
    start: int
    end: int
    kind: str
    is_async: bool = False


class NodeSymbolIndex:
    """Definitions as the instrumenter indexed them, against the ORIGINAL sources."""

    def __init__(
        self, repo_root: Path, source_roots: list[Path], test_roots: list[Path], index_file: Path
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.source_roots = [p.resolve() for p in source_roots]
        self.test_roots = [p.resolve() for p in test_roots]
        doc = json.loads(index_file.read_text())
        self._defs: list[Definition] = [
            Definition(
                d["symbol"], d["path"], d["start"], d["end"], d["kind"], d.get("is_async", False)
            )
            for d in doc["definitions"]
        ]
        self._by_symbol = {d.symbol: d for d in self._defs}
        self._by_path: dict[str, list[Definition]] = {}
        for d in self._defs:
            self._by_path.setdefault(d.path, []).append(d)

    def definitions(self, rel_path: str) -> list[Definition]:
        return self._by_path.get(rel_path, [])

    def symbols_at(self, rel_path: str, lines: set[int]) -> list[Definition]:
        hits: dict[SymbolId, Definition] = {}
        for line in lines:
            covering = [d for d in self.definitions(rel_path) if d.start <= line <= d.end]
            funcs = [d for d in covering if d.kind == "function"]
            pick = (
                max(funcs, key=lambda d: d.start)
                if funcs
                else (max(covering, key=lambda d: d.start) if covering else None)
            )
            if pick:
                hits[pick.symbol] = pick
        return sorted(hits.values(), key=lambda d: (d.path, d.start))

    def find(self, symbol: SymbolId) -> Definition | None:
        return self._by_symbol.get(symbol)

    def source(self, symbol: SymbolId, context: int = 0) -> str | None:
        d = self.find(symbol)
        if d is None:
            return None
        lines = (self.repo_root / d.path).read_text(encoding="utf-8").splitlines()
        lo, hi = max(0, d.start - 1 - context), min(len(lines), d.end + context)
        return "\n".join(f"{i + 1:5d}  {lines[i]}" for i in range(lo, hi))

    def enclosing_class(self, symbol: SymbolId) -> Definition | None:
        d = self.find(symbol)
        if d is None:
            return None
        classes = [
            c for c in self.definitions(d.path)
            if c.kind == "class" and c.start <= d.start and c.end >= d.end and c.symbol != d.symbol
        ]  # fmt: skip
        return max(classes, key=lambda c: c.start) if classes else None

    def module_of(self, symbol: SymbolId) -> str | None:
        d = self.find(symbol)
        if d is None:
            return None
        return d.path.rsplit(".", 1)[0]  # e.g. src/api/services/PetService

    def tests_importing(self, module: str, limit: int = 3) -> list[str]:
        needle = module.split("/")[-1]  # PetService
        hits: list[str] = []
        for root in self.test_roots:
            for file in sorted(root.rglob("*.test.ts")) + sorted(root.rglob("*.spec.ts")):
                try:
                    text = file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if f"/{needle}'" in text or f'/{needle}"' in text:
                    hits.append(str(file.resolve().relative_to(self.repo_root)))
                if len(hits) >= limit:
                    return hits
        return hits


class NodeJestRuntime:
    name = "node/jest"

    def __init__(
        self, repo: Path, source_root: str, test_root: str, tests: str, node: Path | None = None
    ) -> None:
        self.repo = repo.resolve()
        self.source_root = source_root
        self.test_root = test_root
        self.tests = tests
        which = shutil.which("node")
        found = node or (Path(which) if which else None)
        if found is None:
            raise RuntimeError("node not found on PATH")
        self.node = found.resolve()
        self.index_file: Path | None = None

    # ------------------------------------------------------------------ preparation

    def prepare(self, ws: Workspace) -> SymbolIndex:
        # Dependencies are the target's environment (like a venv): linked read-only, never copied.
        nm = self.repo / "node_modules"
        if nm.is_dir() and not (ws.repo / "node_modules").exists():
            os.symlink(nm, ws.repo / "node_modules")
        index_file = ws.root / "symbol-index.json"
        result = subprocess.run(
            [
                str(self.node),
                str(TOOLS / "instrument.js"),
                "--root",
                str(ws.repo),
                "--src",
                self.source_root,
                "--tests",
                self.test_root,
                "--runtime",
                str(TOOLS / "runtime.js"),
                "--index",
                str(index_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        (ws.root / "instrument.log").write_text(result.stdout + result.stderr)
        self.index_file = index_file
        self._write_jest_config(ws)
        return NodeSymbolIndex(
            self.repo, [self.repo / self.source_root], [self.repo / self.test_root], index_file
        )

    def _jest_major(self) -> int:
        try:
            pkg = json.loads((self.repo / "node_modules" / "jest" / "package.json").read_text())
            return int(str(pkg["version"]).split(".")[0])
        except (OSError, KeyError, ValueError):
            return 29

    def _write_jest_config(self, ws: Workspace) -> None:
        setup = str(TOOLS / "jest-setup.js")
        major = self._jest_major()
        base_expr = (
            'require("./package.json").jest || {}'
            if (ws.repo / "package.json").is_file()
            and "jest" in json.loads((ws.repo / "package.json").read_text())
            else ('require("./jest.config.js")' if (ws.repo / "jest.config.js").is_file() else "{}")
        )
        if major < 24:
            # The original setup file is chained by jest-setup.js via DIFFGENOME_CHAIN_SETUP.
            hook = f"  setupTestFrameworkScriptFile: {json.dumps(setup)},\n"
        else:
            hook = (
                f"  setupFilesAfterEnv: [{json.dumps(setup)}]"
                ".concat(base.setupFilesAfterEnv || []),\n"
            )
        shim = TOOLS / "node_modules" / "bcryptjs"
        mapper = ""
        if shim.is_dir():
            # bcrypt's native binding does not build on this Node; the pure-JS port is an
            # external substitution and is recorded as such in the run notes.
            mapper = (
                "  moduleNameMapper: Object.assign({}, base.moduleNameMapper || {}, "
                f'{{ "^bcrypt$": {json.dumps(str(shim))} }}),\n'
            )
        (ws.repo / "diffgenome.jest.config.js").write_text(
            f"const base = {base_expr};\n"
            "module.exports = Object.assign({}, base, {\n"
            "  rootDir: __dirname,\n"
            f"{hook}{mapper}"
            "});\n"
        )
        self._chain_setup = None
        if major < 24:
            base = (
                json.loads((ws.repo / "package.json").read_text()).get("jest", {})
                if (ws.repo / "package.json").is_file()
                else {}
            )
            original = base.get("setupTestFrameworkScriptFile")
            if original:
                self._chain_setup = str(ws.repo / original.replace("<rootDir>/", ""))

    # ------------------------------------------------------------------ execution

    def trace(
        self, ws: Workspace, out_dir: Path, stimulus: Stimulus, only: list[str] | None
    ) -> tuple[list[Execution], str, str]:
        tag = "existing" if stimulus is Stimulus.EXISTING_TEST else "probe"
        traces_ws = ws.root / f"traces-{tag}-{len(list(ws.root.glob('traces-*')))}"
        traces_ws.mkdir(parents=True, exist_ok=True)
        env = {
            "DIFFGENOME_OUT": str(traces_ws),
            "DIFFGENOME_RUNTIME": str(TOOLS / "runtime.js"),
            "DIFFGENOME_STIMULUS": stimulus.value,
            "NODE_OPTIONS": "--max-old-space-size=2048",
            "CI": "1",
        }
        if getattr(self, "_chain_setup", None):
            env["DIFFGENOME_CHAIN_SETUP"] = self._chain_setup or ""
        argv = [
            str(self.node), str(ws.repo / "node_modules" / "jest" / "bin" / "jest.js"),
            "--config", "diffgenome.jest.config.js", "--runInBand", "--forceExit",
            *(only if only else [self.tests]),
        ]  # fmt: skip
        result = ws.run(argv, env=env, timeout=1800, allow_loopback=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_probe_traces(traces_ws, out_dir)
        executions = [execution_from_json(f.read_text()) for f in sorted(out_dir.glob("*.json"))]
        return executions, result.stdout, result.stderr

    def probe_relpath(self, tag: str) -> str:
        return f"{self.test_root}/diffgenome_probe_{tag}.test.ts"

    def conventions(self, index: SymbolIndex) -> str:
        major = self._jest_major()
        rel = os.path.relpath(self.repo / self.source_root, self.repo / self.test_root)
        parts = [
            f"Runtime: Node.js {self._node_version()}, TypeScript, Jest {major} (TypeScript is "
            f"compiled by the repository's own preprocessor, no type checking). The probe is a "
            f"Jest test file named *.test.ts placed directly in {self.test_root}/, so imports of "
            f"the source use '{rel}/...' (for example '{rel}/lib/logger/Logger'). Use ES imports "
            f"at the top of the file like the existing tests do."
        ]
        if major < 24:
            parts.append(
                f"Jest {major} API caveats: jest.isolateModules, setupFilesAfterEnv and "
                "expect().resolves/rejects-with-toMatchObject on older matchers may not exist; "
                "use jest.mock(path, factory) at top level, jest.fn(), jest.resetModules() + "
                "require(), and async test bodies."
            )
        pkg = self.repo / "package.json"
        if pkg.is_file():
            doc = json.loads(pkg.read_text())
            jest_cfg = doc.get("jest")
            if jest_cfg:
                parts.append("jest config (package.json):\n" + json.dumps(jest_cfg, indent=1)[:800])
        return "\n\n".join(parts)

    def _node_version(self) -> str:
        try:
            return subprocess.run(
                [str(self.node), "--version"], capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return "?"
