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
