"""Framework-agnostic diagnostics helpers."""

from __future__ import annotations

from collections import deque
from pathlib import Path


def read_log_tail(path: Path, max_lines: int = 250) -> dict[str, object]:
    """Return the last bounded log lines without loading the whole file."""
    limit = max(20, min(int(max_lines), 1000))
    if not path.exists():
        return {"lines": [], "path": str(path)}

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = deque((line.rstrip("\n") for line in handle), maxlen=limit)
    return {"lines": list(lines), "path": str(path)}


__all__ = ["read_log_tail"]
