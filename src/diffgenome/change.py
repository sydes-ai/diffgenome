"""Change-centred analysis: from a diff (or an explicit symbol) to changed symbols.

Diff parsing is language-neutral (paths and line ranges on the new side). Mapping lines
to symbols goes through a `SymbolIndex`, which a language adapter implements.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from diffgenome.model import SymbolId


class Located(Protocol):
    @property
    def symbol(self) -> SymbolId: ...


class SymbolIndex(Protocol):
    def symbols_at(self, rel_path: str, lines: set[int]) -> Sequence[Located]: ...


@dataclass(frozen=True)
class ChangedRange:
    path: str
    lines: frozenset[int]  # new-side line numbers; empty for pure deletions


@dataclass
class ChangeSet:
    description: str
    ranges: list[ChangedRange]
    symbols: list[SymbolId]
    unmapped_paths: list[str]  # changed files no symbol could be mapped for (non-code, deleted)


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_unified_diff(text: str) -> list[ChangedRange]:
    ranges: dict[str, set[int]] = {}
    path: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            path = None if target == "/dev/null" else target.removeprefix("b/")
            if path is not None:
                ranges.setdefault(path, set())
        elif line.startswith("@@") and path is not None:
            m = _HUNK.match(line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or "1")
                ranges[path].update(range(start, start + max(count, 1)))
    return [ChangedRange(p, frozenset(ls)) for p, ls in sorted(ranges.items())]


def git_diff(repo: Path, revspec: str) -> str:
    """`revspec` like ``base..head`` or a single commit (diffed against its parent)."""
    spec = revspec if ".." in revspec else f"{revspec}^..{revspec}"
    return subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", spec],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip


def changes_from_diff(text: str, index: SymbolIndex, description: str) -> ChangeSet:
    ranges = parse_unified_diff(text)
    symbols: list[SymbolId] = []
    unmapped: list[str] = []
    for r in ranges:
        defs = index.symbols_at(r.path, set(r.lines)) if r.lines else []
        found = [d.symbol for d in defs]
        if found:
            symbols.extend(s for s in found if s not in symbols)
        else:
            unmapped.append(r.path)
    return ChangeSet(description, ranges, symbols, unmapped)


def changes_from_symbols(symbols: list[SymbolId]) -> ChangeSet:
    return ChangeSet("symbol-centred: " + ", ".join(symbols), [], list(symbols), [])
