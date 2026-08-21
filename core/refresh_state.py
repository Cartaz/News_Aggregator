"""Modello unico dello stato operativo dei refresh."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RefreshScope = Literal["", "all", "feed"]


@dataclass
class RefreshState:
    """Stato autoritativo di un'operazione di refresh."""

    active: bool = False
    scope: RefreshScope = ""
    source_id: str = ""
    current: int = 0
    total: int = 0
    active_feed_ids: set[str] = field(default_factory=set)
    operation_id: int = 0

    def begin(self, scope: RefreshScope, total: int, source_id: str = "") -> None:
        self.operation_id += 1
        self.active = True
        self.scope = scope
        self.source_id = source_id
        self.current = 0
        self.total = max(0, int(total))
        self.active_feed_ids = {source_id} if scope == "feed" and source_id else set()

    def progress(self, current: int, total: int | None = None) -> None:
        if total is not None:
            self.total = max(self.total, max(0, int(total)))
        self.current = max(self.current, max(0, int(current)))
        if self.total:
            self.current = min(self.current, self.total)

    def feed_started(self, source_id: str) -> None:
        if self.active and source_id:
            self.active_feed_ids.add(source_id)

    def feed_finished(self, source_id: str) -> None:
        self.active_feed_ids.discard(source_id)

    def finish(self) -> None:
        if self.total:
            self.current = self.total
        self.active = False
        self.scope = ""
        self.source_id = ""
        self.active_feed_ids.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "scope": self.scope,
            "sourceId": self.source_id,
            "current": self.current,
            "total": self.total,
            "feeds": sorted(self.active_feed_ids),
            "operationId": self.operation_id,
        }


__all__ = ["RefreshScope", "RefreshState"]
