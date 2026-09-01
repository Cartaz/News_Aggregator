"""Controller contracts for persistent mutations outside the caller thread."""

from __future__ import annotations

import threading

from config.settings import Settings
from core.app_controller import AppController
from core.models import FeedSource


class _SettingsManager:
    def __init__(self) -> None:
        self.settings = Settings()

    def register_change_callback(self, callback) -> None:  # type: ignore[no-untyped-def]
        self.callback = callback


class _BlockingMutationFeedManager:
    def __init__(self) -> None:
        self.event_sink = None
        self.started = threading.Event()
        self.release = threading.Event()
        self.thread: threading.Thread | None = None

    def set_event_sink(self, event_sink) -> None:  # type: ignore[no-untyped-def]
        self.event_sink = event_sink

    def add(self, url: str, title: str = "") -> FeedSource:
        self.thread = threading.current_thread()
        self.started.set()
        assert self.release.wait(timeout=2.0)
        return FeedSource(url=url, title=title or url)


def _controller(manager: _BlockingMutationFeedManager) -> AppController:
    return AppController(manager, _SettingsManager())  # type: ignore[arg-type]


def test_add_feed_async_returns_before_persistence_finishes() -> None:
    manager = _BlockingMutationFeedManager()
    controller = _controller(manager)
    caller = threading.current_thread()
    finished = threading.Event()
    outcome: dict[str, object] = {}

    def done(operation_id, result, error) -> None:  # type: ignore[no-untyped-def]
        outcome.update(operation_id=operation_id, result=result, error=error)
        finished.set()

    operation_id = controller.add_feed_async(
        "https://example.com/feed.xml",
        "Example",
        done,
    )

    assert isinstance(operation_id, str) and operation_id
    assert manager.started.wait(timeout=1.0)
    assert finished.is_set() is False
    assert manager.thread is not None
    assert manager.thread is not caller

    manager.release.set()
    assert finished.wait(timeout=1.0)
    assert outcome["operation_id"] == operation_id
    assert isinstance(outcome["result"], FeedSource)
    assert outcome["error"] is None

    controller.shutdown(wait_timeout=1.0)


def test_shutdown_drains_accepted_mutation_and_rejects_new_work() -> None:
    manager = _BlockingMutationFeedManager()
    controller = _controller(manager)
    finished = threading.Event()

    assert controller.add_feed_async(
        "https://example.com/feed.xml",
        on_done=lambda operation_id, result, error: finished.set(),
    )
    assert manager.started.wait(timeout=1.0)

    shutdown_done = threading.Event()
    shutdown_thread = threading.Thread(
        target=lambda: (controller.shutdown(wait_timeout=1.0), shutdown_done.set())
    )
    shutdown_thread.start()
    assert shutdown_done.wait(timeout=0.05) is False

    manager.release.set()
    assert finished.wait(timeout=1.0)
    assert shutdown_done.wait(timeout=1.0)
    shutdown_thread.join(timeout=1.0)

    assert controller.add_feed_async("https://example.com/other.xml") is None
