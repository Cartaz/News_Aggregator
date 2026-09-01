"""Serial background worker for persistent application mutations.

The worker is intentionally small: it owns one FIFO queue and one lazy daemon
thread. Domain operations remain synchronous and transactional in their owning
services; the controller decides which operations must leave the GUI thread.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

MutationOperation = Callable[[], Any]
MutationCompletion = Callable[[Any | None, Exception | None], None]
_Task = tuple[MutationOperation, MutationCompletion]
_STOP = object()


class MutationWorker:
    """Execute persistent mutations serially outside the caller thread."""

    def __init__(self, name: str = "state-mutations") -> None:
        self._name = name
        self._queue: queue.Queue[object] = queue.Queue()
        self._lock = threading.Lock()
        self._accepting = True
        self._stop_queued = False
        self._thread: threading.Thread | None = None

    def submit(
        self,
        operation: MutationOperation,
        completion: MutationCompletion,
    ) -> bool:
        """Queue one operation, starting the worker lazily on first use."""
        with self._lock:
            if not self._accepting:
                return False
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run,
                    daemon=True,
                    name=self._name,
                )
                self._thread.start()
            self._queue.put((operation, completion))
        return True

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            try:
                if task is _STOP:
                    return
                operation, completion = task  # type: ignore[misc]
                result: Any | None = None
                error: Exception | None = None
                try:
                    result = operation()
                except Exception as exc:
                    error = exc
                    logger.exception("Mutazione persistente fallita")
                try:
                    completion(result, error)
                except Exception:
                    logger.exception("Callback completamento mutazione fallita")
            finally:
                self._queue.task_done()

    def shutdown(self, wait_timeout: float = 2.0) -> None:
        """Stop accepting work, drain accepted tasks and join for a bounded time."""
        with self._lock:
            self._accepting = False
            thread = self._thread
            if thread is not None and not self._stop_queued:
                self._stop_queued = True
                self._queue.put(_STOP)

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=max(0.0, wait_timeout))
            if thread.is_alive():
                logger.warning(
                    "Worker mutazioni ancora attivo dopo %.1f secondi di shutdown",
                    wait_timeout,
                )

    @property
    def is_alive(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())


__all__ = [
    "MutationCompletion",
    "MutationOperation",
    "MutationWorker",
]
