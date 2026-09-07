"""Regression contract for signal-driven QML/backend synchronization."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = PROJECT_ROOT / "ui" / "controller.py"
MAIN_QML = PROJECT_ROOT / "ui" / "qml" / "Main.qml"


def test_ui_uses_qt_signals_without_background_polling() -> None:
    adapter = CONTROLLER.read_text(encoding="utf-8")
    qml = MAIN_QML.read_text(encoding="utf-8")
    assert "controller.register_event_listener(self._relay_controller_event)" in adapter
    assert "Qt.ConnectionType.QueuedConnection" in adapter
    assert "refreshChanged = Signal()" in adapter
    assert "filterChanged = Signal()" in adapter
    assert "target: backend.preferences" in qml
    assert "articleSelectionChanged = Signal()" in adapter
    assert "Connections {" in qml
    assert "setInterval" not in qml
    assert "pollBackendState" not in qml
