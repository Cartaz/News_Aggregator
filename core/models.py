"""Modelli dati dell'applicazione.

Definiti come dataclass immutabili o quasi. Il livello core li usa come
tipi di scambio; il livello UI li legge senza mai mutarli direttamente.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


def _utcnow() -> datetime:
    """Restituisce il timestamp UTC corrente (timezone-aware)."""
    return datetime.now(timezone.utc)


def _make_feed_id(url: str) -> str:
    """Genera un ID stabile per un feed a partire dall'URL.

    Args:
        url: URL del feed.

    Returns:
        Hash SHA1 esadecimale di 12 caratteri.
    """
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class FeedItem:
    """Singolo articolo di un feed.

    Attributes:
        id: Identificatore stabile (hash del link).
        source_id: ID del feed di appartenenza.
        title: Titolo dell'articolo.
        link: URL canonico dell'articolo.
        summary: Testo pulito (HTML rimosso), troncato a max_length.
        published: Data di pubblicazione (timezone-aware).
        author: Autore se disponibile.
        read: True se l'utente ha già letto l'articolo.
    """

    id: str
    source_id: str
    title: str
    link: str
    summary: str
    published: datetime
    author: str = ""
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
    ) -> FeedItem:
        """Costruisce un FeedItem calcolando automaticamente l'ID."""
        item_id = hashlib.sha1(link.encode("utf-8")).hexdigest()[:16]
        return cls(
            id=item_id,
            source_id=source_id,
            title=title,
            link=link,
            summary=summary,
            published=published,
            author=author,
        )


@dataclass
class FeedSource:
    """Sorgente feed RSS/Atom aggiunta dall'utente.

    Attributes:
        url: URL del feed.
        title: Titolo del feed (estratto o personalizzato).
        enabled: Se True, il feed viene aggiornato automaticamente.
        last_updated: Timestamp dell'ultimo aggiornamento riuscito.
        last_error: Ultimo messaggio di errore (vuoto se tutto OK).
        items: Lista articoli correnti (più recenti per primi).
        category: Nome della cartella/categoria a cui appartiene; vuoto
            se il feed non è assegnato ad alcuna categoria.
    """

    url: str
    title: str = ""
    enabled: bool = True
    last_updated: datetime | None = None
    last_error: str = ""
    items: list[FeedItem] = field(default_factory=list)
    category: str = ""

    @property
    def id(self) -> str:
        """ID stabile derivato dall'URL."""
        return _make_feed_id(self.url)

    @property
    def unread_count(self) -> int:
        """Numero di articoli non letti."""
        return sum(1 for item in self.items if not item.read)

    def replace_items(self, new_items: Iterable[FeedItem]) -> list[FeedItem]:
        """Sostituisce gli articoli preservando lo stato ``read``.

        Args:
            new_items: Nuova collezione di articoli dal parser.

        Returns:
            Lista degli articoli effettivamente nuovi (mai visti prima).
        """
        previous_ids: dict[str, FeedItem] = {it.id: it for it in self.items}
        new_list: list[FeedItem] = []
        brand_new: list[FeedItem] = []
        for item in new_items:
            if item.id in previous_ids:
                # Preserve read state
                old = previous_ids[item.id]
                new_list.append(
                    FeedItem(
                        id=item.id,
                        source_id=item.source_id,
                        title=item.title,
                        link=item.link,
                        summary=item.summary,
                        published=item.published,
                        author=item.author,
                        read=old.read,
                    )
                )
            else:
                new_list.append(item)
                brand_new.append(item)
        self.items = new_list
        self.last_updated = _utcnow()
        self.last_error = ""
        return brand_new

    def mark_read(self, item_id: str) -> bool:
        """Marca un articolo come letto per ID.

        Returns:
            True se l'articolo è stato trovato e aggiornato.
        """
        for idx, item in enumerate(self.items):
            if item.id == item_id:
                self.items[idx] = FeedItem(
                    id=item.id,
                    source_id=item.source_id,
                    title=item.title,
                    link=item.link,
                    summary=item.summary,
                    published=item.published,
                    author=item.author,
                    read=True,
                )
                return True
        return False


@dataclass(frozen=True)
class FeedCategory:
    """Cartella che raggruppa più sorgenti feed.

    Utile per creare "mega-feed" tematici (es. Tech, Economia, Giochi)
    che aggregano gli articoli di tutti i feed assegnati.

    Attributes:
        name: Nome visualizzato della cartella (univoco).
    """

    name: str

    @property
    def id(self) -> str:
        """ID stabile derivato dal nome (case-insensitive)."""
        return hashlib.sha1(self.name.lower().encode("utf-8")).hexdigest()[:12]


__all__ = ["FeedItem", "FeedSource", "FeedCategory"]
