"""Disposable workspace and confined execution for untrusted target code and probes.

The target repository is copied (never mounted writable) into a workspace; commands run
with a scrubbed environment, resource limits, and an OS sandbox selected per platform
(`select_backend`). Collectors only call `Workspace.run`; they never see the backend.

Security contract every backend enforces (tests/test_sandbox_invariants.py):

- no network beyond the sandbox: external TCP/UDP fails; `allow_loopback` permits localhost
  sockets for servers the tests start themselves (macOS: also host loopback services);
- writes only inside the workspace (the original repository and the user's home are
  read-only to the target; reads are not confined);
- a scrubbed environment: nothing inherited from the caller except what is passed explicitly;
- every child process inherits the confinement;
- CPU, process-count and file-size limits, and a wall-clock timeout;
- no supported sandbox on the host: refuse to run, never run unconfined.

Backends: macOS `sandbox-exec` (Seatbelt profile); Linux `bwrap` (bubblewrap: user, network,
PID, IPC and mount namespaces; read-only root, writable workspace, private /tmp, /run and
/dev). Violations are blocked (EPERM/EROFS/ENETUNREACH) and surface in the test output;
socket attempts are additionally recorded by the Python collector's egress guard.
"""

from __future__ import annotations

import functools
import os
import platform
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_IGNORED_NAMES = frozenset({
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".diffgenome",
})  # fmt: skip


def _ignore(directory: str, names: list[str]) -> set[str]:
    """What the workspace copy leaves out: VCS data, caches, and virtualenvs. A virtualenv
    is recognized by its pyvenv.cfg, never by its name: pdm ships a source package
    `pdm/cli/commands/venv`, and dropping it failed 126 of its tests (pdm #3892)."""
    return {
        n
        for n in names
        if n in _IGNORED_NAMES
        or n.endswith(".pyc")
        or os.path.isfile(os.path.join(directory, n, "pyvenv.cfg"))
    }


class SandboxBackend(Protocol):
    name: str

    def wrap(self, ws: Workspace, inner: list[str], allow_loopback: bool) -> list[str]:
        """The full argv that runs `inner` confined to `ws`."""
        ...


class SeatbeltBackend:
    """macOS: `sandbox-exec` with a deny-by-default Seatbelt profile."""

    name = "macos-seatbelt"
    reaches_host_loopback = True  # allow_loopback admits host localhost services too

    @staticmethod
    def available() -> tuple[bool, str]:
        ok = shutil.which("sandbox-exec") is not None and os.access(
            "/usr/bin/sandbox-exec", os.X_OK
        )
        return ok, "" if ok else "/usr/bin/sandbox-exec not found"

    @staticmethod
    def profile(ws_root: Path, allow_loopback: bool = False) -> str:
        ws = str(ws_root.resolve())
        loopback = (
            '(allow network-bind (local ip "localhost:*"))\n'
            '(allow network-inbound (local ip "localhost:*"))\n'
            '(allow network-outbound (remote ip "localhost:*"))\n'
            if allow_loopback
            else ""
        )
        return f"""(version 1)
(deny default)
(allow process-fork)
(allow process-exec)
(allow signal (target self))
(allow sysctl-read)
(allow mach-lookup)
(allow ipc-posix-shm*)
(allow file-read*)
(allow file-write* (subpath "{ws}"))
(allow file-write* (literal "/dev/null") (literal "/dev/dtracehelper") (regex #"^/dev/tty"))
(deny network*)
{loopback}"""

    def wrap(self, ws: Workspace, inner: list[str], allow_loopback: bool) -> list[str]:
        return ["/usr/bin/sandbox-exec", "-p", self.profile(ws.root, allow_loopback), *inner]


class BubblewrapBackend:
    """Linux: `bwrap` in unprivileged user namespaces. The network namespace holds only its
    own loopback, so external networks and host services are unreachable whether or not
    loopback is allowed; `allow_loopback` matters only for servers started inside."""

    name = "linux-bubblewrap"
    reaches_host_loopback = False

    @staticmethod
    @functools.cache
    def available() -> tuple[bool, str]:
        exe = shutil.which("bwrap")
        if exe is None:
            return False, "bwrap (bubblewrap) is not installed"
        probe = subprocess.run(
            [exe, "--unshare-all", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
             "true"],
            capture_output=True, text=True, timeout=30,
        )  # fmt: skip
        if probe.returncode == 0:
            return True, ""
        detail = (probe.stderr.strip().splitlines() or ["?"])[-1]
        hint = ""
        knob = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
        try:
            if knob.read_text().strip() == "1":
                hint = (
                    " (AppArmor restricts unprivileged user namespaces; allow them with "
                    "`sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`)"
                )
        except OSError:
            pass
        return False, f"bwrap cannot create namespaces: {detail}{hint}"

    _PRIVATE = ("/tmp", "/var/tmp", "/run")

    @classmethod
    def _reexposed(cls, ws: Workspace, inner: list[str]) -> list[str]:
        """Top-level entries of the private directories that the command names (its interpreter's
        virtualenv, say) or that the workspace lists as extra read paths: bound back read-only.
        Everything else there (agent and service sockets, other users' temp files) stays hidden."""
        out: set[str] = set()
        for raw in [*inner, *(str(p) for p in ws.extra_read_paths)]:
            if not raw.startswith("/"):
                continue
            for base in cls._PRIVATE:
                for path in {raw, os.path.realpath(raw)}:
                    rel = os.path.relpath(path, base)
                    if not rel.startswith(".."):
                        top = os.path.join(base, rel.split(os.sep)[0])
                        if top != base and os.path.exists(top):
                            out.add(top)
        return sorted(out)

    def wrap(self, ws: Workspace, inner: list[str], allow_loopback: bool) -> list[str]:
        root = str(ws.root.resolve())
        reexpose = [a for top in self._reexposed(ws, inner) for a in ("--ro-bind", top, top)]
        return [
            str(shutil.which("bwrap")),
            "--unshare-user", "--unshare-net", "--unshare-pid", "--unshare-ipc",
            "--unshare-uts", "--unshare-cgroup-try",
            "--die-with-parent", "--new-session",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            # private, empty: host sockets (docker, dbus, agents) and temp files are not visible
            "--tmpfs", "/tmp", "--tmpfs", "/run", "--tmpfs", "/var/tmp",
            *reexpose,
            "--bind", root, root,  # last: the workspace stays writable even under a re-exposed dir
            "--chdir", str(ws.repo.resolve()),
            *inner,
        ]  # fmt: skip


@functools.cache
def select_backend() -> tuple[SandboxBackend | None, str]:
    """The sandbox for this host, or None with the reason no supported one is usable."""
    system = platform.system()
    candidates: list[type[SeatbeltBackend] | type[BubblewrapBackend]] = (
        [SeatbeltBackend] if system == "Darwin"
        else [BubblewrapBackend] if system == "Linux"
        else []
    )  # fmt: skip
    if not candidates:
        return None, f"no sandbox backend for {system}"
    reasons = []
    for backend in candidates:
        ok, why = backend.available()
        if ok:
            return backend(), backend.name
        reasons.append(why)
    return None, "; ".join(reasons)


CPU_LIMIT_MARKER = "stopped by the sandbox CPU-time limit"


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    seconds: float
    confined: bool


@dataclass
class Workspace:
    root: Path  # disposable directory owned by diffgenome
    repo: Path  # copy of the target inside root
    home: Path
    tmp: Path
    extra_read_paths: list[Path] = field(default_factory=list)  # e.g. the target's interpreter

    @classmethod
    def create(
        cls,
        target_repo: Path,
        base: Path,
        extra_read_paths: list[Path] | None = None,
        rev: str | None = None,
    ) -> Workspace:
        root = base / f"ws-{int(time.time() * 1000)}"
        repo = root / "repo"
        if rev:
            # A specific revision without touching the checkout: `git archive` into the copy.
            repo.mkdir(parents=True)
            archive = subprocess.run(
                ["git", "archive", "--format=tar", rev],
                cwd=target_repo,
                capture_output=True,
                check=True,
            )
            subprocess.run(["tar", "-x", "-C", str(repo)], input=archive.stdout, check=True)
        else:
            # Symlinks are copied as links, not followed: a dangling link (glances'
            # tests-data/ sysfs fixtures) is not an error, and the target of a link that
            # leaves the repository is not copied into the workspace. Following such a link
            # inside the sandbox is subject to the same read policy as any absolute path.
            shutil.copytree(target_repo, repo, ignore=_ignore, symlinks=True)
        home, tmp = root / "home", root / "tmp"
        home.mkdir()
        tmp.mkdir()
        return cls(root, repo, home, tmp, list(extra_read_paths or []))

    def destroy(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    # ------------------------------------------------------------------ confinement

    def command(self, argv: list[str], allow_loopback: bool = False) -> list[str] | None:
        """Wrap argv for confined execution, or None if the host has no supported sandbox.
        `allow_loopback` permits localhost sockets only (in-process test servers); every
        other network access stays denied. Resource limits are applied by `run`."""
        backend, _ = select_backend()
        if backend is None:
            return None
        return backend.wrap(self, list(argv), allow_loopback)

    cpu_seconds = 600  # RLIMIT_CPU for everything run in the workspace

    @staticmethod
    def _limits(
        cpu_seconds: int = 600,
        max_procs: int = 4096,  # macOS counts the whole user; 256 broke Jest's `find` spawn
        file_bytes: int = 1 << 30,
    ) -> None:
        """setrlimit in the child before exec: inherited by the sandbox and everything in it,
        independent of the shell (dash has no `ulimit -u`)."""
        import resource

        for limit, value in (
            (resource.RLIMIT_CPU, cpu_seconds),
            (resource.RLIMIT_NPROC, max_procs),
            (resource.RLIMIT_FSIZE, file_bytes),
        ):
            _soft, hard = resource.getrlimit(limit)
            cap = value if hard == resource.RLIM_INFINITY else min(value, hard)
            resource.setrlimit(limit, (cap, hard))

    def environment(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """No inherited variables: no credentials, no proxies, no shell state."""
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "MPLCONFIGDIR": str(self.tmp),
            "LANG": "C.UTF-8",
        }
        env.update(extra or {})
        return env

    def run(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 900,
        allow_loopback: bool = False,
    ) -> RunResult:
        wrapped = self.command(argv, allow_loopback=allow_loopback)
        if wrapped is None:
            raise RuntimeError("no OS sandbox available on this host; refusing to run unconfined")
        start = time.monotonic()
        try:
            proc = subprocess.run(
                wrapped,
                preexec_fn=functools.partial(self._limits, cpu_seconds=self.cpu_seconds),
                cwd=cwd or self.repo,
                env=self.environment(env),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            stderr = proc.stderr
            if proc.returncode in (-signal.SIGXCPU, 128 + signal.SIGXCPU):
                # RLIMIT_CPU: say so, instead of leaving an empty log to be read as "the
                # tests failed or found nothing" (datachain #2001, #2009 on Linux)
                stderr += f"\n{CPU_LIMIT_MARKER} ({self.cpu_seconds} s of CPU time)"
            return RunResult(proc.returncode, proc.stdout, stderr, time.monotonic() - start, True)
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return RunResult(
                -1, out, err + f"\ntimeout after {timeout}s", time.monotonic() - start, True
            )


def host_supports_confinement() -> bool:
    return select_backend()[0] is not None
