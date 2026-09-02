"""Static architecture contracts for strategic-programming boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
CONFIG_DIR = PROJECT_ROOT / "config"
TESTS_DIR = PROJECT_ROOT / "tests"
CORE_INIT = CORE_DIR / "__init__.py"
EVENT_BUS = CORE_DIR / "event_bus.py"
FEED_FETCHER = CORE_DIR / "feed_fetcher.py"
FEED_DISCOVERY = CORE_DIR / "feed_discovery.py"
APP_CONTROLLER = CORE_DIR / "app_controller.py"
SETTINGS = CONFIG_DIR / "settings.py"
CONSTANTS = CONFIG_DIR / "constants.py"
THEME_MIRROR = CONFIG_DIR / "theme.py"
BRIDGE = PROJECT_ROOT / "ui" / "bridge.py"
WINDOW = PROJECT_ROOT / "ui" / "window.py"
DIALOGS = PROJECT_ROOT / "ui" / "web" / "dialogs.js"
PRODUCTION_EVENT_FILES = (
    CORE_DIR / "feed_manager.py",
    APP_CONTROLLER,
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


def test_controller_and_settings_are_explicit_instances_not_singletons() -> None:
    for path in (APP_CONTROLLER, SETTINGS):
        source = path.read_text(encoding="utf-8")
        assert "_instance" not in source
        assert "def __new__(" not in source


def test_test_suite_does_not_simulate_removed_singletons() -> None:
    offenders: list[str] = []
    forbidden = (
        "AppController._instance =",
        "SettingsManager._instance =",
    )
    for path in TESTS_DIR.rglob("*.py"):
        if path == Path(__file__):
            continue
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in forbidden):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_refresh_interval_presets_are_presentation_only() -> None:
    constants_source = CONSTANTS.read_text(encoding="utf-8")
    dialogs_source = DIALOGS.read_text(encoding="utf-8")

    assert "REFRESH_INTERVAL_OPTIONS_MIN" not in constants_source
    assert "const intervals = [1, 5, 15, 30, 60, 120, 360];" in dialogs_source


def test_web_css_is_the_only_cross_platform_theme_definition() -> None:
    config_init = (CONFIG_DIR / "__init__.py").read_text(encoding="utf-8")
    assert not THEME_MIRROR.exists()
    assert "config.theme" not in config_init
    assert "ThemeColors" not in config_init


def test_feed_fetcher_delegates_site_specific_candidate_knowledge() -> None:
    fetcher_source = FEED_FETCHER.read_text(encoding="utf-8")
    discovery_source = FEED_DISCOVERY.read_text(encoding="utf-8")

    assert "from core.feed_discovery import candidate_feed_urls" in fetcher_source
    assert "candidate_feed_urls(url)" in fetcher_source
    assert "bloomberg.com" not in fetcher_source.lower()
    assert "economist.com" not in fetcher_source.lower()
    assert "www.bloomberg.com" in discovery_source
    assert "www.economist.com" in discovery_source


def test_bridge_delegates_item_scope_rules_to_controller() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert "self._controller.get_items(scope, identifier, limit)" in source
    assert "FeedDefaults.MAX_ITEM_AGE_HOURS" not in source
    assert "datetime.now" not in source


def test_bridge_uses_injected_native_port_without_owning_qt_desktop_api() -> None:
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    window_source = WINDOW.read_text(encoding="utf-8")
    assert "Paths." not in bridge_source
    assert ".read_text(" not in bridge_source
    assert "QDesktopServices" not in bridge_source
    assert "QUrl" not in bridge_source
    assert "open_external_url" not in bridge_source
    assert "self._controller.get_log_tail(max_lines)" in bridge_source
    assert "OpenExternalPort = Callable[[str], tuple[bool, str]]" in bridge_source
    assert "ok, message = self._open_external(normalized)" in bridge_source
    assert "from ui.native_actions import open_external_url" in window_source
    assert "open_external=open_external_url" in window_source


def test_refresh_event_delivery_has_no_timing_based_resync_workaround() -> None:
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    assert "QTimer.singleShot" not in bridge_source
    assert "QTimer" not in bridge_source


def test_ui_layers_do_not_reach_into_settings_manager() -> None:
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    window_source = WINDOW.read_text(encoding="utf-8")
    assert ".settings_manager" not in bridge_source
    assert ".settings_manager" not in window_source
    assert "self._controller.update_settings_async(" in bridge_source
    assert "self._controller.update_settings(changes)" not in bridge_source
    assert "self._controller.persist_window_geometry_async(" in window_source
    assert "self._controller.persist_window_geometry(" not in window_source
