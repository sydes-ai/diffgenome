"""Fixture target repositories must be green on their own before tracing them means anything."""

import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.mark.parametrize("repo", sorted(p.name for p in FIXTURES.iterdir() if p.is_dir()))
def test_fixture_repo_own_suite_passes(repo: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=FIXTURES / repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
