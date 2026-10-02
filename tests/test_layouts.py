# ruff: noqa: E501  (inline fixture sources)
"""End-to-end regression fixtures: `diffgenome change` through the real sandbox on tiny
synthetic repositories, one per project layout or failure found in the field (0.1.4-0.1.7).

Each case builds a git repository with a base and a head commit, runs the CLI exactly as Sydes
does, and checks the runtime contract. Fast (each runs a handful of tests), no network, no
external repositories; the real-repository smoke matrix lives in .github/workflows/smoke.yml.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from diffgenome.sandbox import select_backend

BACKEND, WHY = select_backend()
pytestmark = pytest.mark.skipif(
    BACKEND is None and not os.environ.get("DIFFGENOME_REQUIRE_SANDBOX"),
    reason=f"no sandbox backend: {WHY}",
)
REPO = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)


def change(
    tmp_path: Path, base: dict[str, str], head: dict[str, str], *args: str
) -> dict[str, Any]:
    """Commit `base`, then `head` on top, run `diffgenome change`; the runtime contract."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _write(root, base)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    _write(root, head)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "head")
    out = tmp_path / "out"
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    r = subprocess.run(
        [sys.executable, "-m", "diffgenome", "change", "--repo", str(root), "--diff", "HEAD~1..HEAD",
         "--runtime", "python", "--python", sys.executable, "--out", str(out), *args],
        capture_output=True, text=True, env=env, timeout=600,
    )  # fmt: skip
    artifact = out / "diffgenome-change.json"
    assert artifact.is_file(), r.stdout[-2000:] + r.stderr[-4000:]
    return json.loads(artifact.read_text())["runtime"]


def fn(rt: dict[str, Any], suffix: str) -> dict[str, Any]:
    [f] = [f for f in rt["changed_functions"] if f["symbol"].endswith(suffix)]
    return f


SVC = "def total(xs):\n    return sum(xs)\n"
SVC2 = "def total(xs):\n    return sum(x for x in xs if x)\n"


def test_package_at_the_root(tmp_path: Path) -> None:
    rt = change(
        tmp_path,
        {"app/__init__.py": "", "app/svc.py": SVC,
         "tests/test_svc.py": "from app.svc import total\n\ndef test_t():\n    assert total([1, 2]) == 3\n"},
        {"app/svc.py": SVC2},
        "--source-root", ".", "--test-root", "tests", "--tests", "tests", "--pythonpath", ".",
    )  # fmt: skip
    f = fn(rt, "app.svc.total")
    assert f["executed"] and f["tests"] == ["tests/test_svc.py::test_t"]
    assert rt["universe"]["passed"] == 1


def test_src_layout(tmp_path: Path) -> None:
    rt = change(
        tmp_path,
        {"src/pkg/__init__.py": "", "src/pkg/svc.py": SVC,
         "tests/test_svc.py": "from pkg.svc import total\n\ndef test_t():\n    assert total([1]) == 1\n"},
        {"src/pkg/svc.py": SVC2},
        "--source-root", "src", "--test-root", "tests", "--tests", "tests", "--pythonpath", "src",
    )  # fmt: skip
    assert fn(rt, "pkg.svc.total")["executed"]


def test_per_app_unittest_tests_with_honest_outcomes(tmp_path: Path) -> None:
    """Django-style: tests per app (several --test-root), unittest.TestCase; a failing
    TestCase must be recorded as failed (0.1.3 recorded it as passed)."""
    case = "import unittest\nfrom hc.a.svc import total\n\nclass T(unittest.TestCase):\n"
    rt = change(
        tmp_path,
        {"hc/__init__.py": "", "hc/a/__init__.py": "", "hc/a/svc.py": SVC,
         "hc/a/tests/__init__.py": "",
         "hc/a/tests/test_a.py": case + "    def test_ok(self):\n        self.assertEqual(total([1]), 1)\n",
         "hc/b/__init__.py": "", "hc/b/tests/__init__.py": "",
         "hc/b/tests/test_b.py": case + "    def test_bad(self):\n        self.assertEqual(total([1]), 2)\n"},
        {"hc/a/svc.py": SVC2},
        "--source-root", ".", "--test-root", "hc/a/tests", "--test-root", "hc/b/tests",
        "--tests", "hc", "--pythonpath", ".",
    )  # fmt: skip
    assert rt["universe"]["passed"] == 1 and rt["universe"]["failed"] == 1
    f = fn(rt, "hc.a.svc.total")
    assert f["executed"] and f["origin"] == "repo" and f["tests_total"] == 2


def test_workspace_with_two_source_roots(tmp_path: Path) -> None:
    """uv workspace shape (Baserow): the changed function lives in a member package."""
    rt = change(
        tmp_path,
        {"backend/src/core/__init__.py": "",
         "backend/src/core/api.py": "from ext.plug import total\n\ndef run(xs):\n    return total(xs)\n",
         "plugin/src/ext/__init__.py": "", "plugin/src/ext/plug.py": SVC,
         "backend/tests/test_api.py": "from core.api import run\n\ndef test_run():\n    assert run([2]) == 2\n"},
        {"plugin/src/ext/plug.py": SVC2},
        "--source-root", "backend/src", "--source-root", "plugin/src",
        "--test-root", "backend/tests", "--tests", "backend/tests",
        "--pythonpath", "backend/src", "--pythonpath", "plugin/src",
    )  # fmt: skip
    # a changed function in a workspace member is reported, and its caller in another member
    # is traced (0.1.7 indexed and traced one source root only)
    f = fn(rt, "ext.plug.total")
    assert f["executed"] and [c["symbol"] for c in f["callers"]] == ["py:core.api.run"]


def test_tests_inside_the_package(tmp_path: Path) -> None:
    rt = change(
        tmp_path,
        {"toolz/__init__.py": "", "toolz/svc.py": SVC, "toolz/tests/__init__.py": "",
         "toolz/tests/test_svc.py": "from toolz.svc import total\n\ndef test_t():\n    assert total([3]) == 3\n"},
        {"toolz/svc.py": SVC2},
        "--source-root", ".", "--test-root", "toolz/tests", "--tests", "toolz/tests", "--pythonpath", ".",
    )  # fmt: skip
    f = fn(rt, "toolz.svc.total")
    assert f["executed"] and f["origin"] == "repo"


def test_single_module_with_a_root_test_file(tmp_path: Path) -> None:
    """six: six.py and test_six.py side by side; the test root is one file."""
    rt = change(
        tmp_path,
        {"six.py": SVC, "test_six.py": "from six import total\n\ndef test_t():\n    assert total([4]) == 4\n"},
        {"six.py": SVC2},
        "--source-root", ".", "--test-root", "test_six.py", "--tests", "test_six.py", "--pythonpath", ".",
    )  # fmt: skip
    f = fn(rt, "six.total")
    assert f["executed"] and f["tests"] == ["test_six.py::test_t"]


def test_pytest_config_in_a_subdirectory_is_used(tmp_path: Path) -> None:
    """0.1.4 regression (Baserow): backend/pytest.ini was skipped. Here it declares the test
    file pattern, so no test runs unless pytest uses it."""
    rt = change(
        tmp_path,
        {"backend/pytest.ini": "[pytest]\npython_files = check_*.py\n",
         "backend/app.py": SVC,
         "backend/tests/check_app.py": "from app import total\n\ndef test_t():\n    assert total([5]) == 5\n"},
        {"backend/app.py": SVC2},
        "--source-root", "backend", "--test-root", "backend/tests", "--tests", "backend/tests",
        "--pythonpath", "backend",
    )  # fmt: skip
    assert fn(rt, "app.total")["tests"] == ["backend/tests/check_app.py::test_t"]


def test_warnings_as_errors(tmp_path: Path) -> None:
    """0.1.5 regression (itsdangerous, toolz): filterwarnings = error made DiffGenome's own
    plugin warning fatal."""
    rt = change(
        tmp_path,
        {"pyproject.toml": '[tool.pytest.ini_options]\nfilterwarnings = ["error"]\n',
         "app/__init__.py": "", "app/svc.py": SVC,
         "tests/test_svc.py": "from app.svc import total\n\ndef test_t():\n    assert total([1]) == 1\n"},
        {"app/svc.py": SVC2},
        "--source-root", ".", "--test-root", "tests", "--tests", "tests", "--pythonpath", ".",
    )  # fmt: skip
    assert rt["universe"]["passed"] == 1 and fn(rt, "app.svc.total")["executed"]


THREADED = '''import socket, threading, time
from app.svc import total

def _serve(srv):
    while True:
        conn, _ = srv.accept()
        conn.sendall(str(total([1, 2])).encode())
        conn.close()

def _keep_busy():
    for _ in range(50):
        total([1])
        time.sleep(0.01)

def test_server_thread():
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen()
    threading.Thread(target=_serve, args=(srv,), daemon=True).start()
    threading.Thread(target=_keep_busy, daemon=True).start()  # outlives this test
    assert socket.create_connection(srv.getsockname(), timeout=5).recv(8) == b"3"

def test_next():
    time.sleep(0.2)
    assert total([2]) == 2
'''


def test_threads_that_outlive_their_test(tmp_path: Path) -> None:
    """0.1.7 regression (requests test_lowlevel): server threads running across tests left
    dangling parents, and pruning raised inside pytest, aborting the run."""
    rt = change(
        tmp_path,
        {"app/__init__.py": "", "app/svc.py": SVC, "tests/test_net.py": THREADED},
        {"app/svc.py": SVC2},
        "--source-root", ".", "--test-root", "tests", "--tests", "tests", "--pythonpath", ".",
        "--allow-loopback",
    )  # fmt: skip
    assert rt["universe"]["passed"] == 2 and fn(rt, "app.svc.total")["executed"]


def test_import_time_execution(tmp_path: Path) -> None:
    """A changed function called when the package is imported (conftest imports it): executed,
    marked ran_at_import, credited to no test."""
    pkg = "def _check(v):\n    return v > {n}\n\nOK = _check(2)\n\ndef api():\n    return OK\n"
    rt = change(
        tmp_path,
        {"pkg/__init__.py": pkg.format(n=1), "tests/conftest.py": "import pkg  # noqa\n",
         "tests/test_api.py": "from pkg import api\n\ndef test_api():\n    assert api() in (True, False)\n"},
        {"pkg/__init__.py": pkg.format(n=0)},
        "--source-root", ".", "--test-root", "tests", "--tests", "tests", "--pythonpath", ".",
    )  # fmt: skip
    f = fn(rt, "pkg._check")
    assert f["executed"] and f["ran_at_import"] and f["tests"] == []
    assert [t["id"] for t in rt["universe"]["tests"]] == ["tests/test_api.py::test_api"]


def test_one_unimportable_test_file_does_not_stop_the_others(tmp_path: Path) -> None:
    rt = change(
        tmp_path,
        {"app/__init__.py": "", "app/svc.py": SVC,
         "tests/test_ok.py": "from app.svc import total\n\ndef test_t():\n    assert total([1]) == 1\n",
         "tests/test_broken.py": "import not_installed_anywhere\n"},
        {"app/svc.py": SVC2},
        "--source-root", ".", "--test-root", "tests", "--tests", "tests", "--pythonpath", ".",
    )  # fmt: skip
    assert rt["universe"]["passed"] == 1 and fn(rt, "app.svc.total")["executed"]
