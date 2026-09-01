"""Architecture contracts for asynchronous persistent UI commands."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "ui" / "bridge.py"
CONTROLLER = ROOT / "core" / "app_controller.py"
DIALOGS = ROOT / "ui" / "web" / "dialogs.js"
ARTICLES = ROOT / "ui" / "web" / "articles.js"
APP_JS = ROOT / "ui" / "web" / "app.js"
STATE_JS = ROOT / "ui" / "web" / "state.js"


def test_bridge_does_not_run_feed_persistence_synchronously() -> None:
    source = BRIDGE.read_text(encoding="utf-8")

    for forbidden in (
        "self._controller.add_feed(",
        "self._controller.remove_feed(",
        "self._controller.rename_feed(",
        "self._controller.set_category(",
        "self._controller.mark_read(",
    ):
        assert forbidden not in source

    for required in (
        "self._controller.add_feed_async(",
        "self._controller.remove_feed_async(",
        "self._controller.update_feed_async(",
        "self._controller.mark_read_async(",
        "commandFinished = Signal(str)",
    ):
        assert required in source


def test_feed_edit_is_one_atomic_backend_command() -> None:
    bridge = BRIDGE.read_text(encoding="utf-8")
    dialogs = DIALOGS.read_text(encoding="utf-8")

    assert "def updateFeed(" in bridge
    assert "def renameFeed(" not in bridge
    assert "def setFeedCategory(" not in bridge
    assert "bridgeCommand(\n      'updateFeed'" in dialogs
    assert "bridgeCall('renameFeed'" not in dialogs
    assert "bridgeCall('setFeedCategory'" not in dialogs


def test_frontend_waits_for_persistent_command_completion_signal() -> None:
    state_js = STATE_JS.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    dialogs = DIALOGS.read_text(encoding="utf-8")
    articles = ARTICLES.read_text(encoding="utf-8")

    assert "async function bridgeCommand(method, ...args)" in state_js
    assert "function handleCommandFinished(raw)" in state_js
    assert "state.backend.commandFinished.connect(handleCommandFinished);" in app_js
    assert "bridgeCommand('addFeed'" in dialogs
    assert "bridgeCommand('removeFeed'" in dialogs
    assert "bridgeCommand(\n      'markRead'" in articles


def test_controller_owns_the_serial_mutation_worker() -> None:
    source = CONTROLLER.read_text(encoding="utf-8")

    assert "self._mutation_worker = MutationWorker()" in source
    assert "def _submit_mutation(" in source
    assert "self._mutation_worker.submit(operation, complete)" in source
    assert "self._mutation_worker.shutdown(" in source
