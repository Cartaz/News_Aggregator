"""Controller lifecycle and explicit event-flow regression tests."""

from __future__ import annotations

import threading

from config.settings import Settings
from core.app_controller import AppController
from core.exceptions import RefreshCancelledError


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

    def refresh(self, source_id: str, cancel_event=None) -> int:  # type: ignore[no-untyped-def]
        return 0

    def refresh_all(self, progress_cb=None, cancel_event=None):  # type: ignore[no-untyped-def]
        return {"success": 0, "failed": 0, "errors": []}


class _CancellableFeedManager(_FeedManager):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.cancel_seen = threading.Event()

    def refresh(self, source_id: str, cancel_event=None) -> int:  # type: ignore[no-untyped-def]
        assert cancel_event is not None
        self.started.set()
        if cancel_event.wait(timeout=1.0):
            self.cancel_seen.set()
            raise RefreshCancelledError()
        return 0


def _controller(
    manager: _FeedManager | None = None,
) -> tuple[AppController, _FeedManager]:
    actual_manager = manager or _FeedManager()
    controller = AppController(actual_manager, _SettingsManager())  # type: ignore[arg-type]
    return controller, actual_manager


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


def test_shutdown_signals_running_refresh_cancellation() -> None:
    manager = _CancellableFeedManager()
    controller, _ = _controller(manager)

    assert controller.refresh_feed_async("feed-a") is True
    assert manager.started.wait(timeout=1.0)

    controller.shutdown(wait_timeout=1.0)

    assert manager.cancel_seen.is_set()
    with controller._refresh_lock:
        assert controller._refresh_thread is None
        assert controller._refresh_cancel_event is None


def test_worker_remains_owned_until_completion_callback_returns() -> None:
    controller, _ = _controller()
    callback_started = threading.Event()
    release_callback = threading.Event()

    def done(success: bool, message: str) -> None:
        assert success is True
        callback_started.set()
        release_callback.wait(timeout=2.0)

    assert controller.refresh_feed_async("feed-a", done) is True
    assert callback_started.wait(timeout=1.0)

    with controller._refresh_lock:
        worker = controller._refresh_thread
    assert worker is not None
    assert worker.is_alive()
    assert controller.get_refresh_state()["active"] is False

    # Operational state is finished, but a second worker must not overlap while
    # the completion callback still belongs to the first worker.
    assert controller.refresh_feed_async("feed-b") is False

    release_callback.set()
    worker.join(timeout=1.0)
    assert not worker.is_alive()
    with controller._refresh_lock:
        assert controller._refresh_thread is None


def test_shutdown_waits_for_worker_completion_callback() -> None:
    controller, _ = _controller()
    callback_started = threading.Event()
    release_callback = threading.Event()

    def done(success: bool, message: str) -> None:
        callback_started.set()
        release_callback.wait(timeout=2.0)

    assert controller.refresh_feed_async("feed-a", done) is True
    assert callback_started.wait(timeout=1.0)

    shutdown_done = threading.Event()

    def shutdown_controller() -> None:
        controller.shutdown(wait_timeout=1.0)
        shutdown_done.set()

    shutdown_thread = threading.Thread(target=shutdown_controller)
    shutdown_thread.start()
    assert not shutdown_done.wait(timeout=0.05)

    release_callback.set()
    assert shutdown_done.wait(timeout=1.0)
    shutdown_thread.join(timeout=1.0)
