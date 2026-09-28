"""Go runtime adapter: source instrumentation + `go test`.

Everything Go-specific lives here and in tools/go-collector. The workspace copy gets the
`dg` runtime package copied to `<module>/internal/diffgenome/dg`, its sources rewritten in
place by the instrumenter (built once with the host Go), and `go test` runs inside the
sandbox with the module cache read-only and GOPROXY=off (no network). Generated mock
packages are test origin; their methods claim the sole in-repo definer of the mocked
interface method (a static fact from the MockGen header and the package's method sets).
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

TOOLS = Path(__file__).resolve().parents[3] / "tools" / "go-collector"


@dataclass(frozen=True)
class Definition:
    symbol: SymbolId
    path: str
    start: int
    end: int
    kind: str


class GoSymbolIndex:
    def __init__(
        self, repo_root: Path, source_roots: list[Path], test_roots: list[Path], index_file: Path
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.source_roots = [p.resolve() for p in source_roots]
        self.test_roots = [p.resolve() for p in test_roots]
        doc = json.loads(index_file.read_text())
        self._defs = [
            Definition(d["symbol"], d["path"], d["start"], d["end"], d["kind"])
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
        # go:pkg.Type.Method -> go:pkg.Type
        name = symbol.split(":", 1)[1]
        parts = name.split(".")
        if len(parts) < 3:
            return None
        return self.find("go:" + ".".join(parts[:-1]))

    def return_type_of(self, symbol: SymbolId) -> SymbolId | None:
        return None  # not extracted for this runtime yet

    def module_of(self, symbol: SymbolId) -> str | None:
        d = self.find(symbol)
        return d.path.rsplit("/", 1)[0] if d and "/" in d.path else ("." if d else None)

    def tests_importing(self, module: str, limit: int = 3) -> list[str]:
        # Go tests live in the package directory itself.
        pkg = self.repo_root / module
        hits = (
            sorted(str(f.relative_to(self.repo_root)) for f in pkg.glob("*_test.go"))
            if pkg.is_dir()
            else []
        )
        return hits[:limit]


class GoTestRuntime:
    name = "go/test"

    def __init__(
        self,
        repo: Path,
        source_root: str,
        test_root: str,
        tests: str,
        mock_dirs: list[str] | None = None,
    ) -> None:
        self.repo = repo.resolve()
        self.source_root = source_root
        self.test_root = test_root  # package dir whose tests are the stimuli, e.g. "api"
        self.tests = tests  # go test pattern, e.g. "./api/"
        self.mock_dirs = mock_dirs or []
        which = shutil.which("go")
        if not which:
            raise RuntimeError("go not found on PATH")
        self.go = Path(which).resolve()
        self.module = self._module_path()
        self.gopath = Path(
            subprocess.run(
                [str(self.go), "env", "GOPATH"], capture_output=True, text=True
            ).stdout.strip()
        )
        self.gocache = Path(
            subprocess.run(
                [str(self.go), "env", "GOCACHE"], capture_output=True, text=True
            ).stdout.strip()
        )

    def _module_path(self) -> str:
        for line in (self.repo / "go.mod").read_text().splitlines():
            if line.startswith("module "):
                return line.split()[1]
        raise RuntimeError("go.mod has no module line")

    def prepare(self, ws: Workspace) -> SymbolIndex:
        # runtime package inside the module so no network/module edits are needed
        dst = ws.repo / "internal" / "diffgenome" / "dg"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(TOOLS / "dg" / "dg.go", dst / "dg.go")
        tool = ws.root / "dg-instrument"
        subprocess.run(
            [str(self.go), "build", "-o", str(tool), "./instrument"],
            cwd=TOOLS, check=True, capture_output=True, text=True,
            env={**os.environ, "GOFLAGS": "-mod=mod", "GOPROXY": "off"},
        )  # fmt: skip
        index_file = ws.root / "symbol-index.json"
        result = subprocess.run(
            [
                str(tool), "-root", str(ws.repo), "-module", self.module, "-src", self.source_root,
                "-tests", ",".join(self.mock_dirs), "-index", str(index_file),
            ],
            capture_output=True, text=True, check=True,
        )  # fmt: skip
        (ws.root / "instrument.log").write_text(result.stdout + result.stderr)
        mock_roots = [self.repo / d for d in self.mock_dirs]
        return GoSymbolIndex(
            self.repo,
            [self.repo / self.source_root],
            [self.repo / self.test_root, *mock_roots],
            index_file,
        )

    def trace(
        self, ws: Workspace, out_dir: Path, stimulus: Stimulus, only: list[str] | None
    ) -> tuple[list[Execution], str, str]:
        tag = "existing" if stimulus is Stimulus.EXISTING_TEST else "probe"
        traces_ws = ws.root / f"traces-{tag}-{len(list(ws.root.glob('traces-*')))}"
        traces_ws.mkdir(parents=True, exist_ok=True)
        env = {
            "DIFFGENOME_OUT": str(traces_ws),
            "DIFFGENOME_STIMULUS": stimulus.value,
            "GOPATH": str(self.gopath),
            "GOCACHE": str(ws.root / "gocache"),
            "GOMODCACHE": str(self.gopath / "pkg" / "mod"),
            "GOFLAGS": "-mod=mod",
            "GOPROXY": "off",
            "GOTOOLCHAIN": "local",
            "CGO_ENABLED": "0",
            "PATH": f"{self.go.parent}:/usr/bin:/bin",
        }
        argv = [str(self.go), "test", "-count=1", "-p", "1"]
        if only:
            # a probe file lives in the package dir; run that package, only the probe tests
            pkg = "./" + os.path.dirname(only[0]) + "/"
            argv += ["-run", "DiffgenomeProbe", pkg]
        else:
            argv += [self.tests]
        result = ws.run(argv, env=env, timeout=1800, allow_loopback=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_probe_traces(traces_ws, out_dir)
        executions = [execution_from_json(f.read_text()) for f in sorted(out_dir.glob("*.json"))]
        return executions, result.stdout, result.stderr

    def probe_relpath(self, tag: str) -> str:
        return f"{self.test_root}/diffgenome_probe_{tag}_test.go"

    def conventions(self, index: SymbolIndex) -> str:
        return (
            f"Runtime: Go ({self._go_version()}), the standard `go test` runner with testify "
            "(`require`) and gomock available. The probe is a file named "
            f"diffgenome_probe_*_test.go placed in the package directory `{self.test_root}/` "
            f"(package `{self._package_name()}`), so it can use unexported identifiers of that "
            "package directly; test functions MUST be named TestDiffgenomeProbe... so the "
            f"harness can select them. Module path: {self.module}. No network and no database "
            "are available; substitute the Store with the generated gomock "
            "(`mockdb.NewMockStore(ctrl)`) as the existing tests do."
        )

    def _package_name(self) -> str:
        pkg = self.repo / self.test_root
        for f in sorted(pkg.glob("*.go")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("package "):
                    return line.split()[1]
        return os.path.basename(self.test_root)

    def _go_version(self) -> str:
        try:
            return subprocess.run(
                [str(self.go), "version"], capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return "?"
