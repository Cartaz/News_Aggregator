"""Regression tests for settings persistence outside the Qt caller thread."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.app_controller import AppController


class _FeedManager:
    def __init__(self) -> None:
        self.event_sink = None

    def set_event_sink(self, event_sink) -> None:  # type: ignore[no-untyped-def]
        self.event_sink = event_sink

    def get_all(self):  # type: ignore[no-untyped-def]
        return []


class _BlockingSettingsManager:
    def __init__(self) -> None:
        self.settings = Settings()
        self.started = threading.Event()
        self.release = threading.Event()
        self.thread: threading.Thread | None = None
        self.callback = None

    def register_change_callback(self, callback) -> None:  # type: ignore[no-untyped-def]
        self.callback = callback

    def update(self, changes: dict[str, Any]) -> Settings:
        self.thread = threading.current_thread()
        self.started.set()
        assert self.release.wait(timeout=2.0)
        updated = replace(self.settings)
        for key, value in changes.items():
            setattr(updated, key, value)
        self.settings = updated
        if self.callback is not None:
            self.callback(replace(updated))
        return replace(updated)


def test_settings_update_async_returns_before_persistence_finishes() -> None:
    settings = _BlockingSettingsManager()
    controller = AppController(_FeedManager(), settings)  # type: ignore[arg-type]
    caller = threading.current_thread()
    finished = threading.Event()
    outcome: dict[str, object] = {}

    def done(operation_id, result, error) -> None:  # type: ignore[no-untyped-def]
        outcome.update(operation_id=operation_id, result=result, error=error)
        finished.set()

    operation_id = controller.update_settings_async(
        {"show_unread_only": True},
        done,
    )

    assert isinstance(operation_id, str) and operation_id
    assert settings.started.wait(timeout=1.0)
    assert finished.is_set() is False
    assert settings.thread is not None
    assert settings.thread is not caller

    settings.release.set()
    assert finished.wait(timeout=1.0)
    assert outcome["operation_id"] == operation_id
    assert isinstance(outcome["result"], Settings)
    assert outcome["error"] is None
    assert settings.settings.show_unread_only is True

    controller.shutdown(wait_timeout=1.0)


def test_ui_persistence_paths_use_the_serial_command_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    bridge = (root / "ui" / "bridge.py").read_text(encoding="utf-8")
    window = (root / "ui" / "window.py").read_text(encoding="utf-8")
    app_js = (root / "ui" / "web" / "app.js").read_text(encoding="utf-8")
    dialogs_js = (root / "ui" / "web" / "dialogs.js").read_text(encoding="utf-8")

    assert "self._controller.update_settings_async(" in bridge
    assert "self._controller.update_settings(changes)" not in bridge
    assert "persist_window_geometry_async(" in window
    assert "persist_window_geometry(" not in window

    assert "bridgeCommand('saveSettings'" in app_js
    assert "bridgeCommand('setSidebarWidth'" in app_js
    assert "bridgeCall('saveSettings'" not in app_js
    assert "bridgeCall('setSidebarWidth'" not in app_js
    assert "bridgeCommand('saveSettings'" in dialogs_js
    assert "bridgeCall('saveSettings'" not in dialogs_js
