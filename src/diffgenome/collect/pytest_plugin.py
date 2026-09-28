"""pytest adapter for the CPython collector: traces the call phase of every test and writes
one `Execution` JSON per test.

    python -m pytest -p diffgenome.collect.pytest_plugin \\
        --diffgenome-out OUT --diffgenome-source-root . --diffgenome-test-root tests

The target repository is never written to: pass `-p no:cacheprovider` and set
PYTHONDONTWRITEBYTECODE=1 when the target is mounted read-only.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from diffgenome.collect.py_monitoring import COLLECTOR, Tracer
from diffgenome.model import Execution, Stimulus
from diffgenome.serialize import execution_to_json


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("diffgenome")
    group.addoption("--diffgenome-out", required=True, help="directory for Execution JSON")
    group.addoption(
        "--diffgenome-source-root",
        action="append",
        default=[],
        help="repository source root (repeatable); the first is the repository root",
    )
    group.addoption(
        "--diffgenome-test-root", action="append", default=[], help="test root (repeatable)"
    )


def _revision(cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


class _Plugin:
    def __init__(self, config: pytest.Config) -> None:
        self.out = Path(config.getoption("--diffgenome-out")).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        roots = [Path(p).resolve() for p in config.getoption("--diffgenome-source-root")]
        if not roots:
            roots = [Path(config.rootpath).resolve()]
        tests = [Path(p).resolve() for p in config.getoption("--diffgenome-test-root")]
        self.tracer = Tracer(repo_root=roots[0], source_roots=tuple(roots), test_roots=tuple(tests))
        self.revision = _revision(roots[0])

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_call(self, item: pytest.Item) -> Generator[None, None, None]:
        function = getattr(item, "function", None)
        code = getattr(function, "__code__", None)
        root_symbol = (code and self.tracer.symbol_for_code(code)) or f"py:{item.nodeid}"
        self.tracer.start(root_symbol, code)
        outcome = "passed"
        try:
            return (yield)
        except BaseException:
            outcome = "failed"
            raise
        finally:
            result = self.tracer.stop()
            execution = Execution(
                id=f"{item.nodeid}@{self.revision or 'unknown'}",
                stimulus=Stimulus.EXISTING_TEST,
                stimulus_ref=item.nodeid,
                outcome=outcome,
                revision=self.revision,
                collectors=(COLLECTOR,),
                symbols=result.symbols,
                nodes=result.nodes,
            )
            name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid)
            (self.out / f"{name}.json").write_text(execution_to_json(execution))
            if result.stack_repairs:
                item.add_report_section(
                    "call", "diffgenome", f"stack repairs: {result.stack_repairs}"
                )


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(_Plugin(config), "diffgenome-collector")
