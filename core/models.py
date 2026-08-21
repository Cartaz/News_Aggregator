"""Modelli dati dell'applicazione."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Iterable

from core.item_identity import canonicalize_url, fallback_identity_key, make_item_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_feed_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class FeedItem:
    """Singolo articolo con identità stabile GUID/URL/fallback."""

    id: str
    source_id: str
    title: str
    link: str
    summary: str
    published: datetime
    author: str = ""
    guid: str = ""
    read: bool = False

    @classmethod
    def from_raw(
        cls,
        source_id: str,
        title: str,
        link: str,
        summary: str,
        published: datetime,
        author: str = "",
        guid: str = "",
    ) -> FeedItem:
        """Costruisce un item usando GUID, URL canonico o fallback stabile."""
        canonical_link = canonicalize_url(link)
        item_id = make_item_id(
            source_id=source_id,
            title=title,
            link=canonical_link,
            published=published,
            guid=guid,
        )
        return cls(
            id=item_id,
            source_id=source_id,
            title=title,
            link=canonical_link,
            summary=summary,
            published=published,
            author=author,
            guid=(guid or "").strip(),
        )


@dataclass
class FeedSource:
    """Sorgente feed RSS/Atom aggiunta dall'utente."""

    url: str
    title: str = ""
    enabled: bool = True
    last_updated: datetime | None = None
    last_error: str = ""
    items: list[FeedItem] = field(default_factory=list)
    category: str = ""
    resolved_feed_url: str = ""
    http_etag: str = ""
    http_last_modified: str = ""

    @property
    def id(self) -> str:
        return _make_feed_id(self.url)

    @property
    def unread_count(self) -> int:
        return sum(1 for item in self.items if not item.read)

    def replace_items(self, new_items: Iterable[FeedItem]) -> list[FeedItem]:
        """Sostituisce gli articoli preservando lettura e migrazione ID.

        La riconciliazione usa, nell'ordine: nuovo ID, GUID, URL canonico e
        fallback titolo/data solo per item privi sia di GUID sia di URL.
        Questo permette ai vecchi JSON (ID=SHA1 del link grezzo) di migrare
        senza ripresentare gli articoli come nuovi.
        """
        previous_by_id = {item.id: item for item in self.items}
        previous_by_guid = {
            item.guid: item for item in self.items if item.guid
        }
        previous_by_link = {
            canonicalize_url(item.link): item
            for item in self.items
            if canonicalize_url(item.link)
        }
        previous_by_fallback = {
            fallback_identity_key(item.title, item.published): item
            for item in self.items
            if not item.guid and not canonicalize_url(item.link)
        }

        new_list: list[FeedItem] = []
        brand_new: list[FeedItem] = []
        seen_ids: set[str] = set()
        for item in new_items:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)

            old = previous_by_id.get(item.id)
            if old is None and item.guid:
                old = previous_by_guid.get(item.guid)
            canonical_link = canonicalize_url(item.link)
            if old is None and canonical_link:
                old = previous_by_link.get(canonical_link)
            if old is None and not item.guid and not canonical_link:
                old = previous_by_fallback.get(
                    fallback_identity_key(item.title, item.published)
                )

            if old is not None:
                new_list.append(replace(item, read=old.read))
            else:
                new_list.append(item)
                brand_new.append(item)

        self.items = new_list
        self.last_updated = _utcnow()
        self.last_error = ""
        return brand_new

    def mark_read(self, item_id: str) -> bool:
        for idx, item in enumerate(self.items):
            if item.id == item_id:
                self.items[idx] = replace(item, read=True)
                return True
        return False


@dataclass(frozen=True)
class FeedCategory:
    name: str

    @property
    def id(self) -> str:
        return hashlib.sha1(self.name.lower().encode("utf-8")).hexdigest()[:12]


__all__ = ["FeedItem", "FeedSource", "FeedCategory"]
