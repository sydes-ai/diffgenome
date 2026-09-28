"""Disposable workspace and confined execution for untrusted target code and probes.

The target repository is copied (never mounted writable) into a workspace; commands run
with a scrubbed environment, resource limits, and, where the host supports it, an OS
sandbox that denies network access and writes outside the workspace. On macOS that is
`sandbox-exec` (Seatbelt); on Linux a container/namespace runner belongs here later. If no
OS sandbox is available the runner refuses to execute rather than run unconfined.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".diffgenome", "*.pyc",
)  # fmt: skip


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
            shutil.copytree(target_repo, repo, ignore=_IGNORE, symlinks=False)
        home, tmp = root / "home", root / "tmp"
        home.mkdir()
        tmp.mkdir()
        return cls(root, repo, home, tmp, list(extra_read_paths or []))

    def destroy(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    # ------------------------------------------------------------------ confinement

    def _seatbelt_profile(self, allow_loopback: bool = False) -> str:
        ws = str(self.root.resolve())
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

    def command(
        self,
        argv: list[str],
        cpu_seconds: int = 600,
        max_procs: int = 4096,  # macOS counts the whole user; 256 broke Jest's `find` spawn
        allow_loopback: bool = False,
    ) -> list[str] | None:
        """Wrap argv for confined execution, or None if the host has no supported sandbox.
        `allow_loopback` permits localhost sockets only (in-process test servers); every
        other network access stays denied."""
        limits = f'ulimit -t {cpu_seconds}; ulimit -u {max_procs}; ulimit -f 1048576; exec "$@"'
        inner = ["/bin/sh", "-c", limits, "sh", *argv]
        if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
            return ["/usr/bin/sandbox-exec", "-p", self._seatbelt_profile(allow_loopback), *inner]
        return None

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
                cwd=cwd or self.repo,
                env=self.environment(env),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            return RunResult(
                proc.returncode, proc.stdout, proc.stderr, time.monotonic() - start, True
            )
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return RunResult(
                -1, out, err + f"\ntimeout after {timeout}s", time.monotonic() - start, True
            )


def host_supports_confinement() -> bool:
    return (
        platform.system() == "Darwin"
        and shutil.which("sandbox-exec") is not None
        and os.access("/usr/bin/sandbox-exec", os.X_OK)
    )
