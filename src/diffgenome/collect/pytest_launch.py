"""Run pytest with tracing already on, so code that runs at import is observed.

`python -m diffgenome.collect.pytest_launch <pytest args>` starts the session tracer before
pytest imports anything, then runs pytest. Initial conftest loading and test collection
import the code under test (requests' conftest imports requests; Django loads its apps), and
calls made then (module-level setup, registries, checks) would otherwise never be seen. The
plugin (`pytest_plugin`) adopts this tracer, stops it when collection finishes, and writes
that phase as one execution, `IMPORT_REF`, before tracing each test as usual.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--diffgenome-source-root", action="append", default=[])
    ap.add_argument("--diffgenome-test-root", action="append", default=[])
    ap.add_argument("--diffgenome-repo-root", default=None)
    known, _ = ap.parse_known_args(argv)
    roots = [Path(p).resolve() for p in known.diffgenome_source_root] or [Path.cwd()]
    tests = [Path(p).resolve() for p in known.diffgenome_test_root]
    repo = Path(known.diffgenome_repo_root).resolve() if known.diffgenome_repo_root else roots[0]

    from diffgenome.collect import import_phase
    from diffgenome.collect.py_monitoring import Tracer

    tracer = Tracer(repo_root=repo, source_roots=tuple(roots), test_roots=tuple(tests))
    tracer.start(import_phase.IMPORT_REF, None)
    import_phase.TRACER = tracer  # never import pytest_plugin here (see import_phase)

    import pytest

    return int(pytest.main(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
