"""Regression tests for the controller-owned refresh state."""

from __future__ import annotations

import threading

from config.settings import Settings
from core.app_controller import AppController
from core.models import FeedSource
from core.refresh_state import RefreshState


class _SettingsManager:
    def __init__(self) -> None:
        self.settings = Settings()

    def register_change_callback(self, callback) -> None:  # type: ignore[no-untyped-def]
        self.callback = callback


class _BlockingFeedManager:
    def __init__(self) -> None:
        self.sources = [
            FeedSource("https://example.com/one.xml"),
            FeedSource("https://example.com/two.xml"),
        ]
        self.started = threading.Event()
        self.release = threading.Event()
        self.event_sink = None

    def set_event_sink(self, event_sink) -> None:  # type: ignore[no-untyped-def]
        self.event_sink = event_sink

    def get_all(self):  # type: ignore[no-untyped-def]
        return list(self.sources)

    def refresh_all(self, progress_cb=None, cancel_event=None):  # type: ignore[no-untyped-def]
        assert cancel_event is not None
        self.started.set()
        assert self.release.wait(2)
        total = len(self.sources)
        for current, source in enumerate(self.sources, start=1):
            if progress_cb:
                progress_cb(source.id, current, total)
        return {"success": total, "failed": 0, "errors": []}

    def refresh(self, source_id: str, cancel_event=None) -> int:  # type: ignore[no-untyped-def]
        assert cancel_event is not None
        self.started.set()
        assert self.release.wait(2)
        return 0


def _controller(manager: _BlockingFeedManager) -> AppController:
    AppController._instance = None
    return AppController(manager, _SettingsManager())  # type: ignore[arg-type]


def test_refresh_state_is_monotonic_and_serializable() -> None:
    state = RefreshState()
    state.begin("all", 3)
    state.progress(1, 3)
    state.progress(0, 3)
    state.feed_started("feed-a")

    snapshot = state.snapshot()
    assert snapshot["active"] is True
    assert snapshot["scope"] == "all"
    assert snapshot["current"] == 1
    assert snapshot["total"] == 3
    assert snapshot["feeds"] == ["feed-a"]

    state.finish()
    snapshot = state.snapshot()
    assert snapshot["active"] is False
    assert snapshot["current"] == 3
    assert snapshot["feeds"] == []


def test_global_refresh_state_is_owned_by_controller() -> None:
    manager = _BlockingFeedManager()
    controller = _controller(manager)
    done = threading.Event()

    assert controller.refresh_all_async(lambda result: done.set()) is True
    assert manager.started.wait(1)

    running = controller.get_refresh_state()
    assert running["active"] is True
    assert running["scope"] == "all"
    assert running["current"] == 0
    assert running["total"] == 2
    assert controller.refresh_all_async() is False
    assert controller.refresh_feed_async(manager.sources[0].id) is False

    manager.release.set()
    assert done.wait(2)
    finished = controller.get_refresh_state()
    assert finished["active"] is False
    assert finished["current"] == 2
    assert finished["total"] == 2


def test_single_feed_uses_same_refresh_state_model() -> None:
    manager = _BlockingFeedManager()
    controller = _controller(manager)
    done = threading.Event()
    source = manager.sources[0]

    assert controller.refresh_feed_async(source.id, lambda ok, msg: done.set()) is True
    assert manager.started.wait(1)

    running = controller.get_refresh_state()
    assert running["active"] is True
    assert running["scope"] == "feed"
    assert running["sourceId"] == source.id
    assert running["total"] == 1
    assert running["feeds"] == [source.id]

    manager.release.set()
    assert done.wait(2)
    finished = controller.get_refresh_state()
    assert finished["active"] is False
    assert finished["current"] == 1
    assert finished["total"] == 1
