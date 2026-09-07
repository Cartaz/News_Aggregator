"""Architecture contracts for asynchronous persistent QML commands."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI_CONTROLLER = ROOT / "ui" / "controller.py"
CONTROLLER = ROOT / "core" / "app_controller.py"
APP_DIALOGS = ROOT / "ui" / "qml" / "AppDialogs.qml"
PREFERENCES = ROOT / "ui" / "preferences.py"


def test_qml_adapter_does_not_run_persistent_mutations_synchronously() -> None:
    source = UI_CONTROLLER.read_text(encoding="utf-8")
    for forbidden in (
        "self._controller.add_feed(",
        "self._controller.remove_feed(",
        "self._controller.update_feed(",
        "self._controller.mark_read(",
    ):
        assert forbidden not in source

    for required in (
        "self._controller.add_feed_async(",
        "self._controller.remove_feed_async(",
        "self._controller.update_feed_async(",
        "self._controller.mark_read_async(",
        "_commandRelay = Signal(str, bool, str, str)",
    ):
        assert required in source
    preferences = PREFERENCES.read_text(encoding="utf-8")
    assert "self._controller.update_settings_async(" in preferences
    assert "self._controller.update_settings(" not in preferences
    assert "_commandRelay = Signal(str, bool, str)" in preferences
    assert "@Slot(str, bool, str)" in preferences


def test_feed_edit_is_one_atomic_backend_command() -> None:
    adapter = UI_CONTROLLER.read_text(encoding="utf-8")
    qml = APP_DIALOGS.read_text(encoding="utf-8")
    assert "def updateSelectedFeed(" in adapter
    assert "self._controller.update_feed_async(" in adapter
    assert "rename_feed_async" not in adapter
    assert "set_category_async" not in adapter
    assert "backend.updateSelectedFeed(editTitle.text, editCategory.text)" in qml


def test_worker_completion_is_relayed_to_gui_thread() -> None:
    source = UI_CONTROLLER.read_text(encoding="utf-8")
    assert "Qt.ConnectionType.QueuedConnection" in source
    assert "self._commandRelay.emit(" in source
    assert "error is None" in source
    assert "def _deliver_command(" in source
    assert "operationFinished = Signal(str, bool, str)" in source


def test_controller_owns_the_serial_mutation_worker() -> None:
    source = CONTROLLER.read_text(encoding="utf-8")
    assert "self._mutation_worker = MutationWorker()" in source
    assert "def _submit_mutation(" in source
    assert "self._mutation_worker.submit(operation, complete)" in source
    assert "self._mutation_worker.shutdown(" in source
