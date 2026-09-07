"""Static architecture contracts for strategic-programming boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
CONFIG_DIR = PROJECT_ROOT / "config"
TESTS_DIR = PROJECT_ROOT / "tests"
UI_DIR = PROJECT_ROOT / "ui"
CORE_INIT = CORE_DIR / "__init__.py"
EVENT_BUS = CORE_DIR / "event_bus.py"
FEED_FETCHER = CORE_DIR / "feed_fetcher.py"
FEED_DISCOVERY = CORE_DIR / "feed_discovery.py"
APP_CONTROLLER = CORE_DIR / "app_controller.py"
SETTINGS = CONFIG_DIR / "settings.py"
CONSTANTS = CONFIG_DIR / "constants.py"
THEME = UI_DIR / "qml" / "Theme.qml"
UI_CONTROLLER = UI_DIR / "controller.py"
UI_MODELS = UI_DIR / "models.py"
PREFERENCES = UI_DIR / "preferences.py"
DIAGNOSTICS = UI_DIR / "diagnostics.py"
WINDOW = UI_DIR / "window.py"
APP_DIALOGS = UI_DIR / "qml" / "AppDialogs.qml"
PRODUCTION_EVENT_FILES = (CORE_DIR / "feed_manager.py", APP_CONTROLLER, UI_CONTROLLER)


def test_feed_manager_private_storage_does_not_leak_to_other_core_modules() -> None:
    offenders: list[str] = []
    forbidden = ("manager._sources", "manager._lock", "_feed_manager._sources", "_feed_manager._lock")
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
    for forbidden in ("feed_write_ops", "rename_feed", "set_category", "category_ops", "get_all_items", "list_categories"):
        assert forbidden not in source


def test_controller_and_settings_are_explicit_instances_not_singletons() -> None:
    for path in (APP_CONTROLLER, SETTINGS):
        source = path.read_text(encoding="utf-8")
        assert "_instance" not in source
        assert "def __new__(" not in source


def test_test_suite_does_not_simulate_removed_singletons() -> None:
    offenders: list[str] = []
    forbidden = ("AppController._instance =", "SettingsManager._instance =")
    for path in TESTS_DIR.rglob("*.py"):
        if path == Path(__file__):
            continue
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in forbidden):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_refresh_interval_presets_are_presentation_only() -> None:
    constants_source = CONSTANTS.read_text(encoding="utf-8")
    dialogs_source = APP_DIALOGS.read_text(encoding="utf-8")
    assert "REFRESH_INTERVAL_OPTIONS_MIN" not in constants_source
    assert "model: [1, 5, 15, 30, 60, 120, 360]" in dialogs_source


def test_qml_theme_is_the_single_cross_platform_visual_definition() -> None:
    config_init = (CONFIG_DIR / "__init__.py").read_text(encoding="utf-8")
    assert THEME.is_file()
    assert "config.theme" not in config_init
    assert "ThemeColors" not in config_init
    theme = THEME.read_text(encoding="utf-8")
    assert 'readonly property color surface: "#141414"' in theme
    assert 'readonly property color accent: "#ff6600"' in theme


def test_feed_fetcher_delegates_site_specific_candidate_knowledge() -> None:
    fetcher_source = FEED_FETCHER.read_text(encoding="utf-8")
    discovery_source = FEED_DISCOVERY.read_text(encoding="utf-8")
    assert "from core.feed_discovery import candidate_feed_urls" in fetcher_source
    assert "candidate_feed_urls(url)" in fetcher_source
    assert "bloomberg.com" not in fetcher_source.lower()
    assert "economist.com" not in fetcher_source.lower()
    assert "www.bloomberg.com" in discovery_source
    assert "www.economist.com" in discovery_source


def test_qml_adapter_delegates_item_scope_rules_to_controller() -> None:
    source = UI_CONTROLLER.read_text(encoding="utf-8")
    assert "self._controller.get_items(self._scope_kind, self._scope_id, 500)" in source
    assert "FeedDefaults.MAX_ITEM_AGE_HOURS" not in source
    assert "datetime.now" not in source


def test_qml_adapter_uses_injected_native_port() -> None:
    controller_source = UI_CONTROLLER.read_text(encoding="utf-8")
    main_source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    assert "QDesktopServices" not in controller_source
    assert "QUrl" not in controller_source
    assert "OpenExternalPort = Callable[[str], tuple[bool, str]]" in controller_source
    assert "self._open_external(item.link)" in controller_source
    assert "open_external=open_external_url" in main_source


def test_ui_layers_do_not_reach_into_settings_manager() -> None:
    controller_source = UI_CONTROLLER.read_text(encoding="utf-8")
    preferences_source = PREFERENCES.read_text(encoding="utf-8")
    window_source = WINDOW.read_text(encoding="utf-8")
    assert ".settings_manager" not in controller_source
    assert ".settings_manager" not in preferences_source
    assert ".settings_manager" not in window_source
    assert "self._controller.update_settings_async(" in preferences_source
    assert "self._controller.persist_window_geometry_async(" in window_source


def test_qml_uses_typed_models_instead_of_large_variant_snapshots() -> None:
    controller_source = UI_CONTROLLER.read_text(encoding="utf-8")
    models_source = UI_MODELS.read_text(encoding="utf-8")
    assert "QAbstractListModel" in models_source
    assert "def roleNames" in models_source
    assert "SourceListModel" in controller_source
    assert "ArticleListModel" in controller_source
    assert "json.dumps" not in controller_source


def test_webengine_and_webchannel_are_removed_from_production_ui() -> None:
    production = "\n".join(path.read_text(encoding="utf-8") for path in UI_DIR.glob("*.py"))
    assert "QtWebEngine" not in production
    assert "QWebChannel" not in production
    assert not (UI_DIR / "web").exists()
    assert not (UI_DIR / "bridge.py").exists()
