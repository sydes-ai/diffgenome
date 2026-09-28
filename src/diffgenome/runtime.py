"""The runtime seam: what the language-neutral pipeline needs from a target's runtime.

A `RuntimeAdapter` prepares a workspace copy for capture, runs a stimulus set under the
collector and returns protocol `Execution`s, says where a generated probe file goes, and
describes its conventions to the probe writer. A `SymbolIndex` maps source lines to
symbols with the collector's naming and extracts source for probe context. Nothing above
this module knows which runtime it is driving.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from diffgenome.model import Execution, Stimulus, SymbolId
from diffgenome.sandbox import Workspace


class Definition(Protocol):
    @property
    def symbol(self) -> SymbolId: ...
    @property
    def path(self) -> str: ...
    @property
    def start(self) -> int: ...
    @property
    def end(self) -> int: ...
    @property
    def kind(self) -> str: ...


class SymbolIndex(Protocol):
    repo_root: Path
    test_roots: list[Path]

    def symbols_at(self, rel_path: str, lines: set[int]) -> Sequence[Definition]: ...
    def find(self, symbol: SymbolId) -> Definition | None: ...
    def source(self, symbol: SymbolId, context: int = 0) -> str | None: ...
    def enclosing_class(self, symbol: SymbolId) -> Definition | None: ...
    def module_of(self, symbol: SymbolId) -> str | None: ...
    def tests_importing(self, module: str, limit: int = 3) -> list[str]: ...
    def is_test(self, symbol: SymbolId) -> bool:
        """True when the symbol is defined in test code (test roots, test files, doubles)."""
        ...

    def return_type_of(self, symbol: SymbolId) -> SymbolId | None:
        """Declared return type of a function as an in-repo class symbol, when the source
        states one unambiguously; None otherwise. A static fact with its own provenance."""
        ...


class RuntimeAdapter(Protocol):
    name: str  # e.g. "python/pytest", "node/jest"

    def prepare(self, ws: Workspace) -> SymbolIndex:
        """Make the workspace copy capturable (instrument, write config) and return the
        symbol index for the ORIGINAL repository (line numbers of the un-instrumented source)."""
        ...

    def trace(
        self, ws: Workspace, out_dir: Path, stimulus: Stimulus, only: list[str] | None
    ) -> tuple[list[Execution], str, str]:
        """Run the stimuli (all tests, or the given repo-relative paths) under the collector
        inside the sandbox; return executions, stdout, stderr."""
        ...

    def probe_relpath(self, tag: str) -> str:
        """Repo-relative path where a generated probe file must be written."""
        ...

    def conventions(self, index: SymbolIndex) -> str:
        """Bounded text for the probe writer: framework, config, fixtures, import style."""
        ...
