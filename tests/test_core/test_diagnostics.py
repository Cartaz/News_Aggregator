"""Tests for bounded framework-agnostic diagnostics helpers."""

from __future__ import annotations

from pathlib import Path

from core.diagnostics import read_log_tail


def test_missing_log_returns_empty_tail(tmp_path: Path) -> None:
    path = tmp_path / "missing.log"
    assert read_log_tail(path, 250) == {"lines": [], "path": str(path)}


def test_log_tail_returns_only_requested_recent_lines(tmp_path: Path) -> None:
    path = tmp_path / "app.log"
    path.write_text("\n".join(f"line-{index}" for index in range(40)) + "\n", encoding="utf-8")

    result = read_log_tail(path, 20)

    assert result["path"] == str(path)
    assert result["lines"] == [f"line-{index}" for index in range(20, 40)]


def test_log_tail_clamps_upper_bound(tmp_path: Path) -> None:
    path = tmp_path / "app.log"
    path.write_text("\n".join(str(index) for index in range(1100)), encoding="utf-8")

    result = read_log_tail(path, 5000)

    assert len(result["lines"]) == 1000
    assert result["lines"][0] == "100"
    assert result["lines"][-1] == "1099"
