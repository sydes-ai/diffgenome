"""The runtime-evidence path stands alone: genome/proposer code is optional."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import diffgenome


def test_change_path_does_not_import_genome_modules() -> None:
    code = (
        "import sys, diffgenome.mvp, diffgenome.runtime_evidence, diffgenome.__main__;"
        "print(','.join(m for m in sys.modules if m.startswith('diffgenome.genome')))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


def test_collectors_ship_inside_the_package() -> None:
    root = Path(diffgenome.__file__).parent / "_collectors"
    assert (root / "go" / "instrument" / "main.go").is_file()
    assert (root / "node" / "instrument.js").is_file()


def test_target_pythonpath_exposes_only_the_diffgenome_package(tmp_path: Path) -> None:
    """Installed, the package's parent is the host site-packages: putting it on the target's
    PYTHONPATH shadowed the target's pytest/pydantic with the host's (Baserow, 0.1.0)."""
    from diffgenome.collect.py_runtime import isolated_import_root

    root = isolated_import_root(tmp_path)
    assert [p.name for p in root.iterdir()] == ["diffgenome"]
    assert (root / "diffgenome" / "collect" / "pytest_plugin.py").is_file()
    assert not (root / "diffgenome" / "_collectors").exists()
    assert root.resolve() != Path(diffgenome.__file__).resolve().parents[1]


def test_several_test_roots_all_classify_as_tests(tmp_path: Path) -> None:
    """Django keeps tests per app (hc/accounts/tests, hc/api/tests); one --test-root per app."""
    from diffgenome.collect.py_runtime import PytestRuntime
    from diffgenome.sandbox import Workspace

    for rel in ("hc/accounts/models.py", "hc/accounts/tests/test_a.py", "hc/api/tests/test_b.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("def f():\n    return 1\n")
    rt = PytestRuntime(
        tmp_path, Path("python"), ".", ["hc/accounts/tests", "hc/api/tests"], "hc", []
    )
    ws = Workspace(tmp_path, tmp_path, tmp_path, tmp_path)
    index = rt.prepare(ws)
    assert index.is_test("py:hc.accounts.tests.test_a.f")
    assert index.is_test("py:hc.api.tests.test_b.f")
    assert not index.is_test("py:hc.accounts.models.f")
    assert rt.probe_relpath("x").startswith("hc/accounts/tests/")


def test_pytest_uses_the_config_it_would_use_in_the_repository(tmp_path: Path) -> None:
    """0.1.4 passed --rootdir . and DiffGenome's option values as separate arguments; pytest
    then missed backend/pytest.ini (Baserow: Django settings not configured). The config here
    is only found if pytest looks where the test paths are."""
    import shutil
    import sys

    import pytest as _pytest

    from diffgenome.collect.py_runtime import PytestRuntime
    from diffgenome.model import Stimulus
    from diffgenome.sandbox import Workspace, select_backend

    if select_backend()[0] is None or shutil.which("git") is None:
        _pytest.skip("no sandbox backend")
    target = tmp_path / "t"
    (target / "backend" / "tests").mkdir(parents=True)
    (target / "backend" / "pytest.ini").write_text("[pytest]\npython_files = check_*.py\n")
    (target / "backend" / "app.py").write_text("def f():\n    return 1\n")
    (target / "backend" / "tests" / "check_app.py").write_text(
        "from app import f\n\ndef test_f():\n    assert f() == 1\n"
    )
    rt = PytestRuntime(
        target, Path(sys.executable), "backend", "backend/tests", "backend/tests", [],
        pythonpath=["backend"],
    )
    ws = Workspace.create(target, tmp_path / "ws")
    rt.prepare(ws)
    executions, out, err = rt.trace(ws, tmp_path / "out", Stimulus.EXISTING_TEST, None)
    refs = [e.stimulus_ref for e in executions]
    assert "backend/tests/check_app.py::test_f" in refs, out + err  # repository-relative
    assert "py:<import>" in refs  # import and collection time traced by the launcher
