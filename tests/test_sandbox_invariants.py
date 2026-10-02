"""The sandbox security contract, independent of the backend (macOS Seatbelt, Linux bwrap).

Each test runs untrusted code through `Workspace.run`, the only way collectors execute
targets, and asserts on effects visible from the host: a file that must not appear, a
connection that must not succeed. Skipped when the host has no usable backend."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from diffgenome import sandbox
from diffgenome.sandbox import Workspace, select_backend

BACKEND, WHY = select_backend()
# CI sets DIFFGENOME_REQUIRE_SANDBOX: a missing backend fails these tests instead of skipping
pytestmark = pytest.mark.skipif(
    BACKEND is None and not os.environ.get("DIFFGENOME_REQUIRE_SANDBOX"),
    reason=f"no sandbox backend: {WHY}",
)
PY = sys.executable


@pytest.fixture()
def ws(tmp_path: Path) -> Iterator[Workspace]:
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("X = 1\n")
    w = Workspace.create(target, tmp_path / "workspaces")
    yield w
    w.destroy()


def run_py(ws: Workspace, code: str, allow_loopback: bool = False, **env: str):
    return ws.run([PY, "-c", code], env=env or None, timeout=60, allow_loopback=allow_loopback)


def test_backend_is_reported() -> None:
    assert BACKEND is not None and BACKEND.name in ("macos-seatbelt", "linux-bubblewrap")


# -- filesystem ------------------------------------------------------------------------------


def test_writes_inside_the_workspace_work(ws: Workspace) -> None:
    code = "import os; open('out.txt','w').write('ok'); open(os.environ['TMPDIR'] + '/t','w')"
    r = run_py(ws, code)
    assert r.returncode == 0, r.stderr
    assert (ws.repo / "out.txt").read_text() == "ok"


def test_writes_outside_the_workspace_have_no_effect(ws: Workspace) -> None:
    home_file = Path.home() / f".diffgenome-sandbox-{uuid.uuid4().hex}"
    try:
        r = run_py(ws, f"open({str(home_file)!r}, 'w').write('escaped')")
        assert r.returncode != 0
        assert not home_file.exists()
    finally:
        home_file.unlink(missing_ok=True)


def test_the_original_repository_is_never_written(ws: Workspace, tmp_path: Path) -> None:
    original = tmp_path / "target" / "app.py"
    r = run_py(ws, f"open({str(original)!r}, 'w').write('X = 2')")
    assert original.read_text() == "X = 1\n"
    assert r.returncode != 0 or BACKEND.name == "linux-bubblewrap"  # /tmp is private on Linux


def test_child_processes_inherit_the_confinement(ws: Workspace) -> None:
    home_file = Path.home() / f".diffgenome-sandbox-{uuid.uuid4().hex}"
    try:
        inner = f"open({str(home_file)!r}, 'w').write('escaped')"
        r = ws.run(["/bin/sh", "-c", f'"{PY}" -c "{inner}"'], timeout=60)
        assert r.returncode != 0 and not home_file.exists()
    finally:
        home_file.unlink(missing_ok=True)


# -- network ---------------------------------------------------------------------------------

TCP_OUT = "import socket; socket.create_connection(('1.1.1.1', 80), timeout=5); print('CONNECTED')"
UDP_OUT = (
    "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
    "s.sendto(b'x', ('8.8.8.8', 53)); print('SENT')"
)


@pytest.mark.parametrize("allow_loopback", [False, True])
def test_no_external_tcp(ws: Workspace, allow_loopback: bool) -> None:
    r = run_py(ws, TCP_OUT, allow_loopback=allow_loopback)
    assert "CONNECTED" not in r.stdout and r.returncode != 0


@pytest.mark.parametrize("allow_loopback", [False, True])
def test_no_external_udp(ws: Workspace, allow_loopback: bool) -> None:
    r = run_py(ws, UDP_OUT, allow_loopback=allow_loopback)
    assert "SENT" not in r.stdout and r.returncode != 0


def test_loopback_servers_inside_the_sandbox_work_when_allowed(ws: Workspace) -> None:
    code = (
        "import socket, threading\n"
        "srv = socket.socket(); srv.bind(('127.0.0.1', 0)); srv.listen()\n"
        "threading.Thread(target=lambda: srv.accept()[0].sendall(b'hi'), daemon=True).start()\n"
        "c = socket.create_connection(srv.getsockname(), timeout=5); print(c.recv(2).decode())\n"
    )
    r = run_py(ws, code, allow_loopback=True)
    assert r.stdout.strip() == "hi", r.stderr


@pytest.fixture()
def host_service() -> Iterator[int]:
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    srv.settimeout(10)

    def serve() -> None:
        try:
            conn, _ = srv.accept()
            conn.sendall(b"host")
            conn.close()
        except OSError:
            pass

    threading.Thread(target=serve, daemon=True).start()
    yield srv.getsockname()[1]
    srv.close()


@pytest.mark.parametrize("allow_loopback", [False, True])
def test_host_loopback_services(ws: Workspace, host_service: int, allow_loopback: bool) -> None:
    code = (
        f"import socket; c = socket.create_connection(('127.0.0.1', {host_service}), timeout=5); "
        "print(c.recv(4).decode())"
    )
    r = run_py(ws, code, allow_loopback=allow_loopback)
    reachable = r.stdout.strip() == "host"
    # never without allow_loopback; with it only where the backend shares the host loopback
    assert reachable == (allow_loopback and BACKEND.reaches_host_loopback), r.stderr


def test_host_unix_sockets_are_unreachable(ws: Workspace) -> None:
    d = tempfile.mkdtemp(dir="/tmp", prefix="dgs")
    path = os.path.join(d, "s")
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(path)
    srv.listen()
    try:
        code = (
            f"import socket; c = socket.socket(socket.AF_UNIX); c.connect({path!r}); "
            "print('CONNECTED')"
        )
        r = run_py(ws, code, allow_loopback=True)
        assert "CONNECTED" not in r.stdout and r.returncode != 0
    finally:
        srv.close()
        os.unlink(path)
        os.rmdir(d)


# -- environment and processes ---------------------------------------------------------------


def test_environment_is_scrubbed(ws: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIFFGENOME_TEST_SECRET", "s3cret")
    r = run_py(ws, "import os, json; print(json.dumps(dict(os.environ)))", EXTRA="given")
    assert "s3cret" not in r.stdout and '"EXTRA": "given"' in r.stdout
    assert str(ws.home) in r.stdout  # HOME points into the workspace


def test_host_processes_cannot_be_signalled(ws: Workspace) -> None:
    victim = subprocess.Popen(["sleep", "30"])
    try:
        r = run_py(ws, f"import os, signal; os.kill({victim.pid}, signal.SIGTERM); print('SENT')")
        assert victim.poll() is None and "SENT" not in r.stdout
    finally:
        victim.kill()


def test_refuses_to_run_without_a_backend(ws: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "select_backend", lambda: (None, "none for this test"))
    with pytest.raises(RuntimeError, match="refusing to run unconfined"):
        run_py(ws, "print(1)")


# -- legitimate workloads ------------------------------------------------------------------


def _target(tmp_path: Path, files: dict[str, str]) -> Workspace:
    target = tmp_path / "wl"
    for rel, text in files.items():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(text)
    return Workspace.create(target, tmp_path / "wl-ws")


def test_python_pytest_with_a_nested_subprocess(tmp_path: Path) -> None:
    w = _target(tmp_path, {"tests/test_a.py": (
        "import subprocess, sys\n"
        "def test_child():\n"
        "    cmd = [sys.executable, '-c', 'print(6*7)']\n"
        "    out = subprocess.run(cmd, capture_output=True, text=True)\n"
        "    assert out.stdout.strip() == '42'\n"
    )})
    r = w.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], timeout=120)
    assert r.returncode == 0 and "1 passed" in r.stdout, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("go"), reason="no Go toolchain")
def test_go_test(tmp_path: Path) -> None:
    w = _target(tmp_path, {
        "go.mod": "module example.com/wl\n\ngo 1.21\n",
        "add.go": "package wl\n\nfunc Add(a, b int) int { return a + b }\n",
        "add_test.go": (
            'package wl\n\nimport "testing"\n\n'
            "func TestAdd(t *testing.T) { if Add(2, 3) != 5 { t.Fatal(\"bad\") } }\n"
        ),
    })
    env = {
        "GOCACHE": str(w.root / "gocache"), "GOPATH": str(w.root / "gopath"), "GOFLAGS": "-mod=mod",
        "GOPROXY": "off", "GOTOOLCHAIN": "local", "CGO_ENABLED": "0",
    }
    r = w.run([str(shutil.which("go")), "test", "./..."], env=env, timeout=300, allow_loopback=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("node"), reason="no Node.js")
def test_node_builtin_test_runner(tmp_path: Path) -> None:
    w = _target(tmp_path, {"t.test.js": (
        "const test = require('node:test'); const assert = require('node:assert');\n"
        "test('adds', () => assert.strictEqual(2 + 3, 5));\n"
    )})
    r = w.run([str(shutil.which("node")), "--test", "t.test.js"], timeout=120, allow_loopback=True)
    assert r.returncode == 0 and "pass 1" in r.stdout, r.stdout + r.stderr


def test_resource_limits_apply_inside(ws: Workspace) -> None:
    code = "import resource as r; print(r.getrlimit(r.RLIMIT_CPU)[0], r.getrlimit(r.RLIMIT_NPROC)[0])"  # noqa: E501
    r = run_py(ws, code)
    cpu, nproc = (int(x) for x in r.stdout.split())
    assert 0 < cpu <= 600 and 0 < nproc <= 4096, r.stderr


def test_tools_installed_under_tmp_are_usable(ws: Workspace) -> None:
    """GitHub runners put virtualenvs under /tmp; the Linux backend's private /tmp must still
    show the directories a command names (bound back read-only)."""
    d = Path(tempfile.mkdtemp(dir="/tmp", prefix="dgtool"))
    try:
        tool = d / "bin" / "tool.py"
        tool.parent.mkdir()
        (d / "data.txt").write_text("from-tmp")
        tool.write_text(f"print(open({str(d / 'data.txt')!r}).read())\n")
        r = ws.run([PY, str(tool)], timeout=60)
        assert r.stdout.strip() == "from-tmp", r.stderr
        r = ws.run([PY, "-c", f"open({str(d / 'x')!r}, 'w')"], timeout=60)
        assert not (d / "x").exists()  # visible, never writable
    finally:
        shutil.rmtree(d)


# -- the workspace copy (field study, 0.1.9) -------------------------------------------------


def test_source_packages_named_venv_are_copied(tmp_path: Path) -> None:
    """pdm #3892: `pdm/cli/commands/venv` is source; only real virtualenvs (pyvenv.cfg)
    are left out of the workspace."""
    target = tmp_path / "target"
    (target / "pkg/venv").mkdir(parents=True)
    (target / "pkg/venv/__init__.py").write_text("X = 1\n")
    (target / ".venv/bin").mkdir(parents=True)
    (target / ".venv/pyvenv.cfg").write_text("home = /usr\n")
    (target / "env/bin").mkdir(parents=True)
    (target / "env/pyvenv.cfg").write_text("home = /usr\n")
    w = Workspace.create(target, tmp_path / "ws")
    try:
        assert (w.repo / "pkg/venv/__init__.py").is_file()
        assert not (w.repo / ".venv").exists() and not (w.repo / "env").exists()
    finally:
        w.destroy()


def test_symlinks_are_copied_as_links(tmp_path: Path) -> None:
    """glances #3768: a dangling link in test data is not an error; the target of a link
    leaving the repository is not copied into the workspace (reading through the link is
    the documented read policy, as for any absolute path)."""
    secret = tmp_path / "secret.txt"
    secret.write_text("host secret")
    target = tmp_path / "target"
    (target / "tests-data").mkdir(parents=True)
    (target / "tests-data/driver").symlink_to("../../no/such/driver")
    (target / "tests-data/outside").symlink_to(secret)
    (target / "inside.txt").write_text("in repo")
    (target / "tests-data/inside").symlink_to("../inside.txt")
    w = Workspace.create(target, tmp_path / "ws")
    try:
        assert (w.repo / "tests-data/driver").is_symlink()
        assert (w.repo / "tests-data/outside").is_symlink()  # a link, not a copy of the secret
        r = run_py(w, "print(open('tests-data/inside').read())")
        assert r.returncode == 0 and "in repo" in r.stdout, r.stderr
    finally:
        w.destroy()


def test_the_cpu_limit_is_reported(ws: Workspace) -> None:
    """datachain #2001/#2009 on Linux: a run stopped by RLIMIT_CPU said only "no test
    executions captured"."""
    ws.cpu_seconds = 1
    r = run_py(ws, "while True: pass")
    assert r.returncode != 0
    assert "stopped by the sandbox CPU-time limit" in r.stderr
