"""Under --rev the Python symbol index and mechanics describe the analyzed revision, not the
checkout (which may sit at another revision)."""

import subprocess
import sys
from pathlib import Path

from diffgenome.collect.py_runtime import PytestRuntime
from diffgenome.sandbox import Workspace


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def test_index_follows_rev_not_checkout(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    mod = repo / "src" / "pkg" / "m.py"
    mod.write_text("def old():\n    return 1\n")
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "one")
    first = _git(repo, "rev-parse", "HEAD").strip()
    # the new revision inserts lines above `old` and adds `new` where `old` used to be
    mod.write_text("def new():\n    return 2\n\n\ndef old():\n    return 1\n")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "two")
    second = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-q", first)  # the checkout lags behind the analyzed revision

    ws = Workspace.create(repo, tmp_path / "ws", rev=second)
    try:
        runtime = PytestRuntime(repo, Path(sys.executable), "src", "tests", "tests", [])
        index = runtime.prepare(ws)
        names = [d.symbol for d in index.symbols_at("src/pkg/m.py", {1})]
        assert names == ["py:pkg.m.new"], names
    finally:
        ws.destroy()
