"""pytest adapter for the CPython collector: traces the call phase of every test and writes
one `Execution` JSON per test.

    python -m pytest -p diffgenome.collect.pytest_plugin \\
        --diffgenome-out OUT --diffgenome-source-root . --diffgenome-test-root tests

The target repository is never written to: pass `-p no:cacheprovider` and set
PYTHONDONTWRITEBYTECODE=1 when the target is mounted read-only.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from diffgenome.collect import import_phase
from diffgenome.collect.import_phase import IMPORT_REF
from diffgenome.collect.prune import prune_to_focus
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
        "--diffgenome-focus",
        default=None,
        help="JSON list of changed symbols: keep only the part of each trace that bears on them",
    )
    group.addoption(
        "--diffgenome-allow-loopback",
        action="store_true",
        help="with the egress guard: let connections to loopback addresses through",
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
        self.repo_root = repo_root
        # adopt the tracer pytest_launch started before conftests and collection imported code
        self._import_phase = import_phase.TRACER is not None
        self.tracer = import_phase.TRACER or Tracer(
            repo_root=repo_root, source_roots=tuple(roots), test_roots=tuple(tests)
        )
        self.tracer.install_patch_hook()
        self.stimulus = Stimulus(config.getoption("--diffgenome-stimulus"))
        self.collectors: tuple[Collector, ...] = (COLLECTOR,)
        if config.getoption("--diffgenome-egress-guard"):
            self.tracer.install_egress_guard(config.getoption("--diffgenome-allow-loopback"))
            self.collectors = (COLLECTOR, EGRESS_GUARD)
        self.revision = _revision(roots[0])
        focus = config.getoption("--diffgenome-focus")
        spec = json.loads(Path(focus).read_text(encoding="utf-8")) if focus else None
        self.focus: set[str] | None = set(spec["symbols"]) if spec else None
        self.focus_depth: int = int(spec.get("depth", 2)) if spec else 2
        self._pending: dict[str, Any] = {}  # nodeid -> trace, until pytest reports the outcome

    def _end_import_phase(self) -> None:
        if self._import_phase:
            self._import_phase = False
            self._write(None, IMPORT_REF, self.tracer.stop(), "passed")

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self._end_import_phase()

    def pytest_unconfigure(self, config: pytest.Config) -> None:
        self._end_import_phase()  # collection never finished (interrupted)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_call(self, item: pytest.Item) -> Generator[None, None, None]:
        function = getattr(item, "function", None)
        code = getattr(function, "__code__", None)
        root_symbol = (code and self.tracer.symbol_for_code(code)) or f"py:{item.nodeid}"
        self.tracer.start(root_symbol, code)
        try:
            return (yield)
        finally:
            self._pending[item.nodeid] = self.tracer.stop()

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item, call: pytest.CallInfo[None]
    ) -> Generator[None, pytest.TestReport, pytest.TestReport]:
        # The outcome comes from pytest's report, not from whether the call hook raised:
        # unittest.TestCase tests (Django) record failures without raising there.
        report = yield
        if call.when == "call" and item.nodeid in self._pending:
            outcome = "passed" if report.passed else "skipped" if report.skipped else "failed"
            self._write(item, self._test_ref(item), self._pending.pop(item.nodeid), outcome)
        return report

    def _test_ref(self, item: pytest.Item) -> str:
        """The test's id relative to the repository root: pytest's nodeid is relative to its
        rootdir and drops the path of files outside it (Baserow's enterprise tests under
        backend/pytest.ini became '::test_x')."""
        _, sep, rest = item.nodeid.partition("::")
        try:
            path = Path(item.path).resolve().relative_to(self.repo_root)
        except (ValueError, AttributeError):
            return item.nodeid
        return f"{path.as_posix()}{sep}{rest}" if sep else path.as_posix()

    def _write(self, item: pytest.Item | None, nodeid: str, result: Any, outcome: str) -> None:
        nodes, branches, dropped = result.nodes, result.branches, 0
        if self.focus is not None:
            nodes, branches, dropped = prune_to_focus(
                nodes, branches, self.focus, self.focus_depth
            )
        execution = Execution(
            id=f"{nodeid}@{self.revision or 'unknown'}",
            stimulus=self.stimulus,
            stimulus_ref=nodeid,
            outcome=outcome,
            revision=self.revision,
            collectors=self.collectors,
            symbols=result.symbols,
            nodes=nodes,
            branches=branches,
            diagnostics=(
                ("stack_repairs", str(result.stack_repairs)),
                ("attribution_disagreements", str(result.attribution_disagreements)),
                ("pruned_nodes", str(dropped)),
            ),
        )
        # Sanitized ids can collide (parametrized ids differing only in punctuation)
        # and can exceed filesystem limits; the digest keeps every execution distinct.
        digest = hashlib.sha256(nodeid.encode()).hexdigest()[:12]
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid)[:100]
        (self.out / f"{name}-{digest}.json").write_text(execution_to_json(execution))
        if item is not None and result.stack_repairs:
            item.add_report_section("call", "diffgenome", f"stack repairs: {result.stack_repairs}")


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(_Plugin(config), "diffgenome-collector")
