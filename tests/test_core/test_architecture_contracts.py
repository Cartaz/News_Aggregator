"""Static architecture contracts for strategic-programming boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
BRIDGE = PROJECT_ROOT / "ui" / "bridge.py"


def test_feed_manager_private_storage_does_not_leak_to_other_core_modules() -> None:
    offenders: list[str] = []
    for path in CORE_DIR.glob("*.py"):
        if path.name == "feed_manager.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "._sources" in source or "._lock" in source:
            offenders.append(path.name)
    assert offenders == []


def test_bridge_delegates_item_scope_rules_to_controller() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert "self._controller.get_items(scope, identifier, limit)" in source
    assert "FeedDefaults.MAX_ITEM_AGE_HOURS" not in source
    assert "datetime.now" not in source
