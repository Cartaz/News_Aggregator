"""Handler degli eventi EventBus per la finestra principale.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Tutti i metodi ricevono la finestra come primo
argomento e vengono registrati tramite ``EventBridge`` sul thread Qt.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QMessageBox

from core.exceptions import FeedError
from ui.widgets.status_indicator import StatusIndicator

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class MainWindowHandlers:
    """Container statico di handler eventi per ``MainWindow``.

    I metodi sono statici e ricevono la finestra come primo argomento,
    così possono essere passati direttamente a ``EventBridge.subscribe``.
    """

    @staticmethod
    def on_feed_added(window: MainWindow, data: dict[str, Any]) -> None:
        """Aggiorna la lista sorgenti quando un feed viene aggiunto."""
        source_id: str = data.get("source_id", "")
        try:
            source = window._controller.get_feed(source_id)
            window._source_list.update_source(source)
        except FeedError:
            pass
        # Il nuovo feed non ha ancora articoli, ma aggiorniamo comunque
        # il badge per coerenza (potrebbe aver importato articoli letti)
        window._refresh_tray_badge()

    @staticmethod
    def on_feed_removed(window: MainWindow, data: dict[str, Any]) -> None:
        """Rimuove la sorgente dalla lista quando un feed viene eliminato."""
        source_id: str = data.get("source_id", "")
        window._source_list.remove_source(source_id)
        if window._source_list.get_selected_id() is None:
            window._refresh_news_view(None)
        # Il feed rimosso poteva avere articoli non letti: ricalcola badge
        window._refresh_tray_badge()

    @staticmethod
    def on_refresh_started(window: MainWindow, data: dict[str, Any]) -> None:
        """Mostra lo stato di refresh in corso."""
        url: str = data.get("url", "")
        window._set_status(
            f"Aggiornamento: {url}", StatusIndicator.State.RUNNING
        )

    @staticmethod
    def on_refresh_completed(window: MainWindow, data: dict[str, Any]) -> None:
        """Aggiorna lista e vista articoli al completamento del refresh."""
        source_id: str = data.get("source_id", "")
        try:
            source = window._controller.get_feed(source_id)
            window._source_list.update_source(source)
            if window._source_list.get_selected_id() == source_id:
                window._refresh_news_view(source_id)
        except FeedError:
            pass
        window._set_status(
            f"Aggiornato: {data.get('title', '')} "
            f"({data.get('new_count', 0)} nuovi)",
            StatusIndicator.State.RUNNING,
        )
        # Nuovi articoli possono aver incrementato il totale non letti
        window._refresh_tray_badge()

    @staticmethod
    def on_refresh_failed(window: MainWindow, data: dict[str, Any]) -> None:
        """Imposta lo stato di errore."""
        window._set_status(
            f"Errore: {data.get('error', 'sconosciuto')}",
            StatusIndicator.State.ERROR,
        )

    @staticmethod
    def on_new_items(window: MainWindow, data: dict[str, Any]) -> None:
        """Handler per nuovi articoli — aggiorna badge tray.

        L'utente ha esplicitamente richiesto di NON ricevere notifiche
        di sistema (balloon) dall'app, MA vuole vedere il contatore
        articoli non letti sulla tray icon. Quindi qui aggiorniamo il
        badge invece di mostrare una notifica.
        """
        items: list[dict[str, Any]] = data.get("items", [])
        if items:
            logger.debug(
                "Ricevuti %d nuovi articoli (aggiorno badge tray)",
                len(items),
            )
        window._refresh_tray_badge()

    @staticmethod
    def on_item_read(window: MainWindow, data: dict[str, Any]) -> None:
        """Aggiorna la lista e la tabella quando un articolo è marcato letto.

        Aggiorna:
        - Il nodo sorgente (e i totali dei nodi padre) in ``SourceList``
        - La riga corrispondente in ``NewsView`` (colore testo → secondary)
        - Il badge della tray icon (un articolo in meno da leggere)
        """
        source_id: str = data.get("source_id", "")
        item_id: str = data.get("item_id", "")
        try:
            source = window._controller.get_feed(source_id)
            window._source_list.update_source(source)
        except FeedError:
            pass
        # Aggiorna la riga nella tabella articoli (colore "letto")
        if hasattr(window._news_view, "mark_item_read"):
            window._news_view.mark_item_read(item_id)
        # Un articolo in meno da leggere: decrementa badge
        window._refresh_tray_badge()

    @staticmethod
    def on_feed_renamed(window: MainWindow, data: dict[str, Any]) -> None:
        """Aggiorna la lista quando un feed viene rinominato."""
        source_id: str = data.get("source_id", "")
        try:
            source = window._controller.get_feed(source_id)
            window._source_list.update_source(source)
        except FeedError:
            pass

    @staticmethod
    def on_feed_category_changed(window: MainWindow, data: dict[str, Any]) -> None:
        """Ricostruisce l'albero quando un feed cambia categoria."""
        sources = window._controller.get_all_feeds()
        categories = window._controller.get_categories()
        window._source_list.set_sources(sources, categories)


__all__ = ["MainWindowHandlers"]
