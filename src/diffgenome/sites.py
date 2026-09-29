"""Stable identity of decision (branch) sites.

A site is identified by the repository-relative file and the span of its condition in
the ORIGINAL source: 1-based line and 1-based byte column of the first character, and
1-based line and 1-based byte column just past the last character. Every runtime
(instrumenter or monitor) and every static front end computes the id from the original
source independently, so instrumentation that rewrites code cannot change it.
"""

from __future__ import annotations

import hashlib

Span = tuple[int, int, int, int]  # start line, start col, end line, end col (exclusive)


def site_id(rel_path: str, span: Span) -> str:
    l1, c1, l2, c2 = span
    return "br:" + hashlib.sha256(f"{rel_path}:{l1}:{c1}:{l2}:{c2}".encode()).hexdigest()[:12]
