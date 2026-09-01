"""Tests for the serial persistent-mutation worker."""

from __future__ import annotations

import threading

from core.mutation_worker import MutationWorker


def test_worker_is_lazy_and_executes_fifo_off_caller_thread() -> None:
    worker = MutationWorker("test-mutations")
    caller = threading.current_thread()
    completed = threading.Event()
    lock = threading.Lock()
    executed: list[tuple[int, threading.Thread]] = []
    results: list[int] = []

    assert worker.is_alive is False

    def operation(value: int):  # type: ignore[no-untyped-def]
        def run() -> int:
            with lock:
                executed.append((value, threading.current_thread()))
            return value
        return run

    def completion(result, error) -> None:  # type: ignore[no-untyped-def]
        assert error is None
        results.append(result)
        if len(results) == 2:
            completed.set()

    assert worker.submit(operation(1), completion) is True
    assert worker.submit(operation(2), completion) is True
    assert completed.wait(timeout=1.0)

    worker.shutdown(wait_timeout=1.0)

    assert [value for value, _ in executed] == [1, 2]
    assert results == [1, 2]
    assert all(thread is not caller for _, thread in executed)
    assert worker.is_alive is False


def test_worker_reports_operation_error_and_continues() -> None:
    worker = MutationWorker("test-mutation-errors")
    completed = threading.Event()
    outcomes: list[tuple[object, Exception | None]] = []

    def fail() -> None:
        raise RuntimeError("disk failure")

    def record(result, error) -> None:  # type: ignore[no-untyped-def]
        outcomes.append((result, error))
        if len(outcomes) == 2:
            completed.set()

    assert worker.submit(fail, record) is True
    assert worker.submit(lambda: "ok", record) is True
    assert completed.wait(timeout=1.0)
    worker.shutdown(wait_timeout=1.0)

    assert outcomes[0][0] is None
    assert isinstance(outcomes[0][1], RuntimeError)
    assert outcomes[1] == ("ok", None)


def test_shutdown_rejects_new_mutations() -> None:
    worker = MutationWorker("test-mutation-shutdown")
    worker.shutdown(wait_timeout=0)

    assert worker.submit(lambda: None, lambda result, error: None) is False
