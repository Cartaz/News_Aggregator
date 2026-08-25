"""Controller lifecycle and explicit event-flow regression tests."""

from __future__ import annotations

from config.settings import Settings
from core.app_controller import AppController


class _SettingsManager:
    def __init__(self) -> None:
        self.settings = Settings()

    def register_change_callback(self, callback) -> None:  # type: ignore[no-untyped-def]
        self.callback = callback


class _FeedManager:
    def __init__(self) -> None:
        self.event_sink = None

    def set_event_sink(self, event_sink) -> None:  # type: ignore[no-untyped-def]
        self.event_sink = event_sink

    def get_all(self):  # type: ignore[no-untyped-def]
        return []

    def refresh_all(self, progress_cb=None):  # type: ignore[no-untyped-def]
        return {"success": 0, "failed": 0, "errors": []}


def _controller() -> tuple[AppController, _FeedManager]:
    AppController._instance = None
    manager = _FeedManager()
    controller = AppController(manager, _SettingsManager())  # type: ignore[arg-type]
    return controller, manager


def test_feed_events_flow_through_explicit_controller_listener() -> None:
    controller, manager = _controller()
    received: list[tuple[str, dict]] = []
    controller.register_event_listener(
        lambda event_name, payload: received.append((event_name, payload))
    )

    assert manager.event_sink is not None
    manager.event_sink("feed_added", {"source_id": "feed-a"})

    assert received == [("feed_added", {"source_id": "feed-a"})]


def test_shutdown_detaches_feed_events_and_rejects_new_refreshes() -> None:
    controller, manager = _controller()

    controller.shutdown(wait_timeout=0)

    assert manager.event_sink is None
    assert controller.refresh_all_async() is False
    controller.start_auto_refresh()
    assert controller._auto_timer is None


def test_shutdown_is_idempotent() -> None:
    controller, _ = _controller()

    controller.shutdown(wait_timeout=0)
    controller.shutdown(wait_timeout=0)
