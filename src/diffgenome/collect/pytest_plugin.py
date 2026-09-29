"""pytest adapter for the CPython collector: traces the call phase of every test and writes
one `Execution` JSON per test.

    python -m pytest -p diffgenome.collect.pytest_plugin \\
        --diffgenome-out OUT --diffgenome-source-root . --diffgenome-test-root tests

The target repository is never written to: pass `-p no:cacheprovider` and set
PYTHONDONTWRITEBYTECODE=1 when the target is mounted read-only.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from diffgenome.collect.py_monitoring import COLLECTOR, EGRESS_GUARD, Tracer
from diffgenome.model import Collector, Execution, Stimulus
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
    group.addoption(
        "--diffgenome-repo-root",
        default=None,
        help="repository root that site ids and paths are relative to (default: first source root)",
    )
    group.addoption(
        "--diffgenome-stimulus",
        default="existing_test",
        choices=[s.value for s in Stimulus],
        help="how these executions were caused (generated probes must say so)",
    )
    group.addoption(
        "--diffgenome-egress-guard",
        action="store_true",
        help="refuse socket connects and record attempts as OS-plane evidence",
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
        # Site ids hash the repository-relative path (sites.py); a source root below the
        # repository root (Baserow: backend/src) must not become the base. Experiment 10, F2.
        repo_opt = config.getoption("--diffgenome-repo-root")
        repo_root = Path(repo_opt).resolve() if repo_opt else roots[0]
        self.tracer = Tracer(
            repo_root=repo_root, source_roots=tuple(roots), test_roots=tuple(tests)
        )
        self.tracer.install_patch_hook()
        self.stimulus = Stimulus(config.getoption("--diffgenome-stimulus"))
        self.collectors: tuple[Collector, ...] = (COLLECTOR,)
        if config.getoption("--diffgenome-egress-guard"):
            self.tracer.install_egress_guard()
            self.collectors = (COLLECTOR, EGRESS_GUARD)
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
                stimulus=self.stimulus,
                stimulus_ref=item.nodeid,
                outcome=outcome,
                revision=self.revision,
                collectors=self.collectors,
                symbols=result.symbols,
                nodes=result.nodes,
                branches=result.branches,
                diagnostics=(
                    ("stack_repairs", str(result.stack_repairs)),
                    ("attribution_disagreements", str(result.attribution_disagreements)),
                ),
            )
            # Sanitized ids can collide (parametrized ids differing only in punctuation)
            # and can exceed filesystem limits; the digest keeps every execution distinct.
            digest = hashlib.sha256(item.nodeid.encode()).hexdigest()[:12]
            name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid)[:100]
            (self.out / f"{name}-{digest}.json").write_text(execution_to_json(execution))
            if result.stack_repairs:
                item.add_report_section(
                    "call", "diffgenome", f"stack repairs: {result.stack_repairs}"
                )


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(_Plugin(config), "diffgenome-collector")
