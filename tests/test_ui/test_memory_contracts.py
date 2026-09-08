"""Static memory-efficiency contracts for the Qt Quick presentation layer."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "ui" / "qml"


def test_both_virtualized_lists_disable_delegate_cache_buffers() -> None:
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    assert main.count("reuseItems: true") >= 2
    assert main.count("cacheBuffer: 0") >= 2


def test_dialog_subtrees_are_created_only_while_a_modal_is_open() -> None:
    dialogs = (QML / "AppDialogs.qml").read_text(encoding="utf-8")
    assert "id: modalLoader" in dialogs
    assert "active: root.opened" in dialogs
    assert "sourceComponent: modalFrame" in dialogs
    assert "id: addBody" in dialogs
    assert "id: editBody" in dialogs
    assert "id: removeBody" in dialogs
    assert "id: settingsBody" in dialogs
    assert "id: logBody" in dialogs
    assert "backend.diagnostics.clear()" in dialogs


def test_qml_models_avoid_per_role_mapping_allocations() -> None:
    models = (ROOT / "ui" / "models.py").read_text(encoding="utf-8")
    assert models.count("@dataclass(frozen=True, slots=True)") >= 2
    assert "mapping: dict[int, Any]" not in models
    assert "if not query and not self._unread_only:" in models


def test_tray_releases_recreatable_qt_quick_resources() -> None:
    window = (ROOT / "ui" / "window.py").read_text(encoding="utf-8")
    assert "setPersistentGraphics(False)" in window
    assert "setPersistentSceneGraph(False)" in window
    assert "releaseResources()" in window
    assert "collectGarbage()" in window
    assert "trimComponentCache()" in window
    assert "_memory_trim_timer.start()" in window
    assert "setPersistentGraphics(True)" in window
    assert "setPersistentSceneGraph(True)" in window
