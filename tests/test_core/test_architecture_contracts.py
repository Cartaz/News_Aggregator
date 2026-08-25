"""Static architecture contracts for strategic-programming boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
BRIDGE = PROJECT_ROOT / "ui" / "bridge.py"
PRODUCTION_EVENT_FILES = (
    CORE_DIR / "feed_manager.py",
    CORE_DIR / "app_controller.py",
    CORE_DIR / "feed_write_ops.py",
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


def test_production_event_flow_does_not_depend_on_global_event_bus() -> None:
    offenders: list[str] = []
    for path in PRODUCTION_EVENT_FILES:
        source = path.read_text(encoding="utf-8")
        if "core.event_bus" in source or "EventBus()" in source:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_bridge_delegates_item_scope_rules_to_controller() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert "self._controller.get_items(scope, identifier, limit)" in source
    assert "FeedDefaults.MAX_ITEM_AGE_HOURS" not in source
    assert "datetime.now" not in source
