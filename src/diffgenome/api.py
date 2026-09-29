"""Library surface for integrators (Sydes and others).

`analyze_change` runs the pipeline for one change and returns the ``diffgenome-change/1``
artifact as a dict; `load_change_artifact` reads one back. Everything an integrator needs is
in the artifact; nothing here exposes collectors, corpora or graphs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diffgenome.change_artifact import FORMAT

ARTIFACT_FILENAME = "diffgenome-change.json"
MAP_FILENAME = "behavioral-map.md"


class ChangeAnalysisError(RuntimeError):
    """The pipeline could not produce an artifact (no executions, unsupported runtime, ...)."""


def analyze_change(
    repo: str | Path,
    *,
    runtime: str,
    diff: str | None = None,
    symbols: list[str] | None = None,
    rev: str | None = None,
    out: str | Path,
    runtime_args: list[str] | None = None,
    probes: int = 0,
    attempts: int = 1,
    writer: str = "none",
    up: int = 3,
    down: int = 4,
) -> dict[str, Any]:
    """Run DiffGenome on one change and return the artifact. `runtime_args` are the
    runtime adapter's own options (`--test-root`, `--tests`, `--mock-dir`, `--python`,
    `--pytest-arg`, `--source-root`); the integrator forwards them opaquely. `probes` is the
    budget: 0 means existing tests only, no LLM call."""
    from diffgenome.mvp import main as mvp_main

    argv = [
        "--runtime", runtime, "--repo", str(repo), "--out", str(out), "--writer", writer,
        "--probes", str(probes), "--attempts", str(attempts), "--up", str(up), "--down", str(down),
    ]  # fmt: skip
    if diff:
        argv += ["--diff", diff]
    for s in symbols or []:
        argv += ["--symbol", s]
    if rev:
        argv += ["--rev", rev]
    argv += list(runtime_args or [])
    code = mvp_main(argv)
    path = Path(out) / ARTIFACT_FILENAME
    if code != 0 or not path.is_file():
        raise ChangeAnalysisError(f"diffgenome exited {code}; no {ARTIFACT_FILENAME} in {out}")
    return load_change_artifact(path)


def load_change_artifact(path: str | Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(Path(path).read_text())
    if doc.get("format") != FORMAT:
        raise ChangeAnalysisError(f"{path}: not a {FORMAT} artifact (format={doc.get('format')!r})")
    return doc
