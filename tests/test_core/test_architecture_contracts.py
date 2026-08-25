"""Static architecture contracts for strategic-programming boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
CORE_INIT = CORE_DIR / "__init__.py"
EVENT_BUS = CORE_DIR / "event_bus.py"
BRIDGE = PROJECT_ROOT / "ui" / "bridge.py"
WINDOW = PROJECT_ROOT / "ui" / "window.py"
PRODUCTION_EVENT_FILES = (
    CORE_DIR / "feed_manager.py",
    CORE_DIR / "app_controller.py",
    BRIDGE,
)


def test_feed_manager_private_storage_does_not_leak_to_other_core_modules() -> None:
    offenders: list[str] = []
    forbidden = (
        "manager._sources",
        "manager._lock",
        "_feed_manager._sources",
        "_feed_manager._lock",
    )
    for path in CORE_DIR.glob("*.py"):
        if path.name == "feed_manager.py":
            continue
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in forbidden):
            offenders.append(path.name)
    assert offenders == []


def test_global_event_bus_module_is_not_part_of_the_architecture() -> None:
    assert not EVENT_BUS.exists()


def test_production_event_flow_does_not_depend_on_global_event_bus() -> None:
    offenders: list[str] = []
    for path in PRODUCTION_EVENT_FILES:
        source = path.read_text(encoding="utf-8")
        if "core.event_bus" in source or "EventBus()" in source:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_core_public_surface_exposes_owned_abstractions_not_compatibility_helpers() -> None:
    source = CORE_INIT.read_text(encoding="utf-8")
    assert "feed_write_ops" not in source
    assert "rename_feed" not in source
    assert "set_category" not in source
    assert "category_ops" not in source
    assert "get_all_items" not in source
    assert "list_categories" not in source


def test_bridge_delegates_item_scope_rules_to_controller() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert "self._controller.get_items(scope, identifier, limit)" in source
    assert "FeedDefaults.MAX_ITEM_AGE_HOURS" not in source
    assert "datetime.now" not in source


def test_bridge_does_not_own_filesystem_or_native_desktop_integration() -> None:
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    window_source = WINDOW.read_text(encoding="utf-8")
    assert "Paths." not in bridge_source
    assert ".read_text(" not in bridge_source
    assert "QDesktopServices" not in bridge_source
    assert "QUrl" not in bridge_source
    assert "open_external_url" not in bridge_source
    assert "self._controller.get_log_tail(max_lines)" in bridge_source
    assert "requestOpenExternal = Signal(str)" in bridge_source
    assert "self.requestOpenExternal.emit(normalized)" in bridge_source
    assert "from ui.native_actions import open_external_url" in window_source
    assert "self.bridge.requestOpenExternal.connect(self._open_external)" in window_source


def test_ui_layers_do_not_reach_into_settings_manager() -> None:
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    window_source = WINDOW.read_text(encoding="utf-8")
    assert ".settings_manager" not in bridge_source
    assert ".settings_manager" not in window_source
    assert "self._controller.update_settings(changes)" in bridge_source
    assert "self._controller.persist_window_geometry" in window_source
