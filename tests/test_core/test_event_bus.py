"""Test per core/event_bus.py."""

from __future__ import annotations

from core.event_bus import EventBus


def test_subscribe_and_emit(reset_event_bus: None) -> None:
    """L'emit deve richiamare gli handler registrati."""
    received: list[dict] = []
    bus: EventBus = EventBus()
    bus.subscribe("test_event", lambda data: received.append(data))
    bus.emit("test_event", {"key": "value"})
    assert len(received) == 1
    assert received[0]["key"] == "value"


def test_unsubscribe(reset_event_bus: None) -> None:
    """La deregistrazione deve fermare le notifiche."""
    received: list[dict] = []
    bus: EventBus = EventBus()
    handler = lambda data: received.append(data)
    bus.subscribe("test_event", handler)
    bus.unsubscribe("test_event", handler)
    bus.emit("test_event", {"key": "value"})
    assert received == []


def test_multiple_handlers(reset_event_bus: None) -> None:
    """Più handler devono essere richiamati in ordine di registrazione."""
    calls: list[str] = []
    bus: EventBus = EventBus()
    bus.subscribe("evt", lambda d: calls.append("first"))
    bus.subscribe("evt", lambda d: calls.append("second"))
    bus.emit("evt")
    assert calls == ["first", "second"]


def test_handler_exception_does_not_block(reset_event_bus: None) -> None:
    """Un'eccezione in un handler non deve bloccare gli altri."""
    calls: list[str] = []
    bus: EventBus = EventBus()

    def bad_handler(_: dict) -> None:
        raise RuntimeError("boom")

    bus.subscribe("evt", bad_handler)
    bus.subscribe("evt", lambda d: calls.append("ok"))
    bus.emit("evt")
    assert calls == ["ok"]


def test_handler_count(reset_event_bus: None) -> None:
    """handler_count deve restituire il numero corretto."""
    bus: EventBus = EventBus()
    assert bus.handler_count("evt") == 0
    bus.subscribe("evt", lambda d: None)
    assert bus.handler_count("evt") == 1
    bus.subscribe("evt", lambda d: None)
    assert bus.handler_count("evt") == 2


def test_no_handlers_silent(reset_event_bus: None) -> None:
    """Emit senza handler non deve sollevare eccezioni."""
    bus: EventBus = EventBus()
    bus.emit("nonexistent_event", {"data": 1})


def test_singleton_identity(reset_event_bus: None) -> None:
    """Bus deve essere singleton: stessa istanza."""
    bus1: EventBus = EventBus()
    bus2: EventBus = EventBus()
    assert bus1 is bus2
