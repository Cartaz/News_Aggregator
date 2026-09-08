"""Regression tests for measured Linux/glibc memory controls."""

from __future__ import annotations

from pathlib import Path

from core import native_memory

ROOT = Path(__file__).resolve().parents[2]


def test_allocator_bootstrap_reexecs_linux_once_with_bounded_arenas(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    calls: list[tuple[str, list[str], dict[str, str]]] = []

    monkeypatch.setattr(native_memory.sys, "platform", "linux")
    monkeypatch.setattr(native_memory.sys, "executable", "/venv/bin/python")
    monkeypatch.setattr(native_memory.sys, "argv", ["main.py", "--example"])
    monkeypatch.delenv("MALLOC_ARENA_MAX", raising=False)
    monkeypatch.setattr(
        native_memory.os,
        "execve",
        lambda executable, argv, environment: calls.append(
            (executable, list(argv), dict(environment))
        ),
    )

    native_memory.bootstrap_allocator()

    assert len(calls) == 1
    executable, argv, environment = calls[0]
    assert executable == "/venv/bin/python"
    assert argv == ["/venv/bin/python", "main.py", "--example"]
    assert environment["MALLOC_ARENA_MAX"] == "2"


def test_allocator_bootstrap_respects_explicit_user_value(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(native_memory.sys, "platform", "linux")
    monkeypatch.setenv("MALLOC_ARENA_MAX", "4")
    monkeypatch.setattr(
        native_memory.os,
        "execve",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("execve must not run")
        ),
    )

    native_memory.bootstrap_allocator()


def test_trim_process_memory_uses_resolved_malloc_trim(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    pads: list[int] = []

    def fake_trim(pad: int) -> int:
        pads.append(pad)
        return 1

    monkeypatch.setattr(native_memory, "_malloc_trim_resolved", True)
    monkeypatch.setattr(native_memory, "_malloc_trim_function", fake_trim)

    assert native_memory.trim_process_memory() is True
    assert pads == [0]


def test_main_bootstraps_allocator_before_qt_imports() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert source.index("bootstrap_allocator()") < source.index("from PySide6")
    assert 'event_name == "refresh_state_changed"' in source
    assert "trim_process_memory()" in source
