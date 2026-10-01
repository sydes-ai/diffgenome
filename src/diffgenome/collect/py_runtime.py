"""Python/pytest runtime adapter: the CPython collector as a `RuntimeAdapter`."""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

from diffgenome.collect.py_symbols import PythonSymbolIndex
from diffgenome.model import Execution, Stimulus
from diffgenome.probe import copy_probe_traces
from diffgenome.runtime import SymbolIndex
from diffgenome.sandbox import Workspace
from diffgenome.serialize import execution_from_json

DIFFGENOME_PACKAGE = Path(__file__).resolve().parents[1]


def isolated_import_root(ws_root: Path) -> Path:
    """A directory holding only the `diffgenome` package, for the target's PYTHONPATH.

    The package's parent is `src/` in a checkout but the whole host `site-packages` when
    installed; putting that on the target's PYTHONPATH would shadow the target's own
    packages (pytest, pydantic, ...) with the host's, built for another interpreter.
    """
    root = ws_root / "diffgenome-import"
    if not (root / "diffgenome").is_dir():
        shutil.copytree(
            DIFFGENOME_PACKAGE, root / "diffgenome",
            ignore=shutil.ignore_patterns("__pycache__", "_collectors", "node_modules"),
        )
    return root


class PytestRuntime:
    name = "python/pytest"

    def __init__(
        self,
        repo: Path,
        python: Path,
        source_root: str,
        test_root: str,
        tests: str,
        pytest_args: list[str],
        pythonpath: list[str] | None = None,
        test_env: dict[str, str] | None = None,
        allow_loopback: bool = False,
    ) -> None:
        self.repo = repo
        self.python = python
        self.source_root = source_root
        self.test_root = test_root
        self.tests = tests
        self.pytest_args = pytest_args
        # Generic target-environment options (experiment 10, Baserow): repo-relative import
        # roots resolved inside the disposable workspace; allow-listed, non-secret test
        # variables (e.g. a local disposable database); loopback-only networking for local
        # services. Target code still runs under the OS sandbox with no other network.
        self.pythonpath = list(pythonpath or [])
        self.test_env = dict(test_env or {})
        self.allow_loopback = allow_loopback

    def prepare(self, ws: Workspace) -> SymbolIndex:
        # Index the workspace copy, i.e. the analyzed revision (`--rev` archives it there), not
        # the checkout: the checkout may sit at another revision, and the index maps the
        # change's diff lines and the executed code's locations onto symbols.
        return PythonSymbolIndex(ws.repo, [ws.repo / self.source_root], [ws.repo / self.test_root])

    def trace(
        self, ws: Workspace, out_dir: Path, stimulus: Stimulus, only: list[str] | None
    ) -> tuple[list[Execution], str, str]:
        tag = "existing" if stimulus is Stimulus.EXISTING_TEST else "probe"
        traces_ws = ws.root / f"traces-{tag}-{len(list(ws.root.glob('traces-*')))}"
        traces_ws.mkdir(parents=True, exist_ok=True)
        argv = [
            str(self.python), "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "-p", "diffgenome.collect.pytest_plugin",
            "--diffgenome-out", str(traces_ws),
            "--diffgenome-repo-root", ".",
            "--diffgenome-source-root", self.source_root,
            "--diffgenome-test-root", self.test_root,
            "--diffgenome-stimulus", stimulus.value,
            "--diffgenome-egress-guard",
            *self.pytest_args,
            *(only if only else [self.tests]),
        ]  # fmt: skip
        roots = [str(ws.repo / p) for p in self.pythonpath]
        roots.append(str(isolated_import_root(ws.root)))
        env = {**self.test_env, "PYTHONPATH": ":".join(roots)}
        result = ws.run(argv, env=env, timeout=1800, allow_loopback=self.allow_loopback)
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_probe_traces(traces_ws, out_dir)
        executions = [execution_from_json(f.read_text()) for f in sorted(out_dir.glob("*.json"))]
        return executions, result.stdout, result.stderr

    def probe_relpath(self, tag: str) -> str:
        return f"{self.test_root}/test_diffgenome_probe_{tag}.py"

    def conventions(self, index: SymbolIndex) -> str:
        parts = ["Runtime: Python, pytest. The probe is a pytest test file."]
        for root in index.test_roots:
            f = root / "conftest.py"
            if f.is_file():
                lines: list[str] = []
                try:
                    tree = ast.parse(f.read_text(encoding="utf-8"))
                except SyntaxError:
                    tree = None
                for node in tree.body if tree else []:
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and any(
                        "fixture" in ast.unparse(d) for d in node.decorator_list
                    ):
                        doc = ast.get_docstring(node) or ""
                        params = ", ".join(a.arg for a in node.args.args)
                        lines.append(
                            f"- {node.name}({params}): {doc.splitlines()[0] if doc else ''}"
                        )
                if lines:
                    parts.append("conftest fixtures available:\n" + "\n".join(lines[:30]))
        ini = index.repo_root / "pytest.ini"
        if ini.is_file():
            parts.append(
                "pytest.ini:\n" + "\n".join(ini.read_text(encoding="utf-8").splitlines()[:20])
            )
        pyproject = index.repo_root / "pyproject.toml"
        if pyproject.is_file():
            text = pyproject.read_text(encoding="utf-8")
            if "[tool.pytest" in text:
                parts.append(
                    "pyproject pytest section:\n"
                    + "\n".join(text[text.index("[tool.pytest") :].splitlines()[:15])
                )
        return "\n\n".join(parts)
