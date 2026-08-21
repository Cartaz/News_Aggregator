"""Regression test per il refresh concorrente limitato (roadmap A3)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from config.constants import FeedDefaults
from core.exceptions import FeedError
from core.feed_manager import FeedManager


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    return FeedManager()


def test_refresh_all_uses_bounded_concurrency(manager: FeedManager) -> None:
    """Più feed devono sovrapporsi senza superare il limite configurato."""
    sources = [
        manager.add(f"https://example.com/feed-{index}.xml")
        for index in range(8)
    ]
    lock = threading.Lock()
    barrier = threading.Barrier(FeedDefaults.REFRESH_MAX_WORKERS, timeout=2)
    active = 0
    max_active = 0
    called: list[str] = []
    workers: list[threading.Thread] = []

    def fake_refresh(source_id: str) -> int:
        nonlocal active, max_active
        worker = threading.current_thread()
        with lock:
            workers.append(worker)
            called.append(source_id)
            active += 1
            max_active = max(max_active, active)
        barrier.wait()
        time.sleep(0.02)
        with lock:
            active -= 1
        return 0

    with patch.object(manager, "refresh", side_effect=fake_refresh):
        result = manager.refresh_all()

    assert max_active == FeedDefaults.REFRESH_MAX_WORKERS
    assert len(called) == len(sources)
    assert len(set(called)) == len(sources)
    assert set(called) == {source.id for source in sources}
    assert result == {"success": 8, "failed": 0, "errors": []}
    assert all(worker.name.startswith("feed-refresh") for worker in workers)
    assert all(not worker.is_alive() for worker in workers)


def test_refresh_all_isolates_feed_errors(manager: FeedManager) -> None:
    """Un feed fallito non deve interrompere gli altri worker."""
    ok = manager.add("https://example.com/ok.xml")
    expected = manager.add("https://example.com/expected-error.xml")
    unexpected = manager.add("https://example.com/unexpected-error.xml")
    progress: list[tuple[str, int, int]] = []

    def fake_refresh(source_id: str) -> int:
        if source_id == expected.id:
            raise FeedError("errore previsto")
        if source_id == unexpected.id:
            raise RuntimeError("errore inatteso")
        return 0

    with patch.object(manager, "refresh", side_effect=fake_refresh):
        result = manager.refresh_all(
            lambda source_id, completed, total: progress.append(
                (source_id, completed, total)
            )
        )

    assert result["success"] == 1
    assert result["failed"] == 2
    assert len(result["errors"]) == 2
    assert any("errore previsto" in error for error in result["errors"])
    assert any("errore inatteso" in error for error in result["errors"])
    assert [completed for _, completed, _ in progress] == [1, 2, 3]
    assert {source_id for source_id, _, _ in progress} == {
        ok.id,
        expected.id,
        unexpected.id,
    }
    assert all(total == 3 for _, _, total in progress)


def test_progress_callback_failure_does_not_abort_refresh(manager: FeedManager) -> None:
    """Un errore della UI nel callback progresso non deve fermare il pool."""
    for index in range(3):
        manager.add(f"https://example.com/{index}.xml")

    callback_calls = 0

    def broken_progress(_source_id: str, _completed: int, _total: int) -> None:
        nonlocal callback_calls
        callback_calls += 1
        raise RuntimeError("UI callback failure")

    with patch.object(manager, "refresh", return_value=0):
        result = manager.refresh_all(broken_progress)

    assert callback_calls == 3
    assert result == {"success": 3, "failed": 0, "errors": []}
