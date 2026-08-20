"""Azioni utente della finestra principale.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Tutti i metodi ricevono la finestra come primo
argomento e sono invocati dai segnali Qt connessi nella finestra.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMessageBox

from config.constants import Shortcuts
from core.exceptions import FeedDuplicateError, FeedError
from core.models import FeedItem, FeedSource
from ui.widgets.status_indicator import StatusIndicator

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class MainWindowActions:
    """Container statico di azioni utente per ``MainWindow``.

    I metodi sono statici e ricevono la finestra come primo argomento,
    così possono essere passati direttamente a ``signal.connect``.
    """

    @staticmethod
    def add_feed(window: MainWindow, url: str) -> None:
        """Aggiunge un nuovo feed URL e avvia il primo refresh."""
        try:
            source: FeedSource = window._controller.add_feed(url)
            window._source_list.add_source(source)
            window._set_status(
                f"Aggiunto: {source.title or source.url}",
                StatusIndicator.State.RUNNING,
            )
            window._controller.refresh_feed_async(source.id)
        except FeedDuplicateError:
            QMessageBox.information(
                window,
                "Feed già presente",
                f"L'URL è già nella raccolta:\n{url}",
            )
        except FeedError as exc:
            QMessageBox.warning(window, "Errore", str(exc))

    @staticmethod
    def refresh_all(window: MainWindow) -> None:
        """Avvia il refresh di tutti i feed in background.

        Il callback ``on_done`` emette il segnale ``refresh_all_done``
        che Qt marshalla automaticamente al main thread. Questo evita
        di toccare widget Qt dal worker thread (che causava
        ``QBasicTimer::start: Timers cannot be started from another
        thread`` e SIGSEGV).
        """
        window._set_status(
            "Aggiornamento di tutti i feed…",
            StatusIndicator.State.RUNNING,
        )
        window._refresh_all_btn.set_enabled(False)
        window._controller.refresh_all_async(
            on_done=lambda r: window.refresh_all_done.emit(r)
        )

    @staticmethod
    def _refresh_all_done(window: MainWindow, result: dict[str, Any]) -> None:
        """Callback Qt-safe al termine del refresh tutti (main thread)."""
        window._refresh_all_btn.set_enabled(True)
        success: int = result.get("success", 0)
        failed: int = result.get("failed", 0)
        sources: list[FeedSource] = window._controller.get_all_feeds()
        categories: list[str] = window._controller.get_categories()
        window._source_list.set_sources(sources, categories)
        state = (
            StatusIndicator.State.RUNNING
            if success > 0
            else StatusIndicator.State.STOPPED
        )
        if failed:
            state = StatusIndicator.State.ERROR
        window._set_status(
            f"Aggiornamento completato: {success} OK, {failed} errori",
            state,
        )

    @staticmethod
    def refresh_single_by_id(window: MainWindow, source_id: str) -> None:
        """Aggiorna un singolo feed dato l'ID.

        Il callback ``on_done`` emette il segnale ``refresh_single_done``
        che Qt marshalla automaticamente al main thread.
        """
        window._set_status(
            "Aggiornamento feed…", StatusIndicator.State.RUNNING
        )
        window._controller.refresh_feed_async(
            source_id,
            on_done=lambda ok, msg: window.refresh_single_done.emit(
                source_id, ok, msg
            ),
        )

    @staticmethod
    def _single_done(
        window: MainWindow,
        source_id: str,
        success: bool,
        message: str,
    ) -> None:
        """Callback al termine del refresh singolo."""
        try:
            source: FeedSource = window._controller.get_feed(source_id)
            window._source_list.update_source(source)
            if window._source_list.get_selected_id() == source_id:
                window._refresh_news_view(source_id)
        except FeedError as exc:
            logger.error("Feed non più disponibile: %s", exc)
            return
        state = (
            StatusIndicator.State.RUNNING
            if success
            else StatusIndicator.State.ERROR
        )
        window._set_status(message, state)

    @staticmethod
    def remove_feed(window: MainWindow) -> None:
        """Rimuove il feed selezionato (con conferma)."""
        source_id: str | None = window._source_list.get_selected_id()
        if not source_id:
            return
        MainWindowActions.remove_by_id(window, source_id)

    @staticmethod
    def remove_by_id(window: MainWindow, source_id: str) -> None:
        """Rimuove un feed dato l'ID (con conferma)."""
        try:
            source: FeedSource = window._controller.get_feed(source_id)
        except FeedError:
            return
        reply: QMessageBox.StandardButton = QMessageBox.question(
            window,
            "Conferma eliminazione",
            f"Eliminare il feed:\n{source.title or source.url}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            window._controller.remove_feed(source_id)
            window._source_list.remove_source(source_id)
            window._refresh_news_view(None)
            window._set_status(
                "Feed eliminato", StatusIndicator.State.STOPPED
            )
        except FeedError as exc:
            QMessageBox.warning(window, "Errore", str(exc))

    @staticmethod
    def source_selected(window: MainWindow, source_id: str) -> None:
        """Cambia la vista articoli alla sorgente selezionata."""
        window._refresh_news_view_by_source(source_id)

    @staticmethod
    def all_selected(window: MainWindow) -> None:
        """Mostra il mega-feed con tutti gli articoli di tutte le sorgenti."""
        window._refresh_news_view_all()

    @staticmethod
    def category_selected(window: MainWindow, category: str) -> None:
        """Mostra gli articoli aggregati della categoria selezionata.

        Args:
            window: Finestra principale.
            category: Nome categoria; stringa vuota per "Senza categoria".
        """
        window._refresh_news_view_by_category(category)

    @staticmethod
    def rename_feed(window: MainWindow, source_id: str, new_title: str) -> None:
        """Rinomina una sorgente feed."""
        try:
            source: FeedSource = window._controller.rename_feed(
                source_id, new_title
            )
            window._source_list.update_source(source)
            window._set_status(
                f"Rinominato in: {source.title}",
                StatusIndicator.State.RUNNING,
            )
        except FeedError as exc:
            QMessageBox.warning(window, "Errore", str(exc))

    @staticmethod
    def change_category(
        window: MainWindow, source_id: str, new_category: str
    ) -> None:
        """Assegna o rimuove la categoria di una sorgente."""
        try:
            source: FeedSource = window._controller.set_category(
                source_id, new_category
            )
            # Ricostruisci tutto l'albero per riflettere lo spostamento
            sources: list[FeedSource] = window._controller.get_all_feeds()
            categories: list[str] = window._controller.get_categories()
            window._source_list.set_sources(sources, categories)
            window._set_status(
                f"Categoria aggiornata: {new_category or '(nessuna)'}",
                StatusIndicator.State.RUNNING,
            )
        except FeedError as exc:
            QMessageBox.warning(window, "Errore", str(exc))

    @staticmethod
    def item_activated(
        window: MainWindow, source_id: str, item_id: str
    ) -> None:
        """Marca l'articolo come letto (se impostazioni lo richiedono)."""
        if not window._controller.settings.mark_read_on_select:
            return
        try:
            window._controller.mark_read(source_id, item_id)
        except FeedError as exc:
            logger.warning("Impossibile marcare come letto: %s", exc)

    @staticmethod
    def open_in_browser(window: MainWindow, url: str) -> None:
        """Apre l'URL nel browser esterno di sistema.

        Usa ``QUrl.fromUserInput()`` invece di ``QUrl()`` diretto per
        gestire correttamente URL con caratteri non ASCII, spazi, o
        schemi non standard. ``fromUserInput`` normalizza l'input ed
        è la funzione raccomandata da Qt per URL provenienti da fonti
        non affidabili (feed RSS, input utente, ecc.).

        Args:
            window: Finestra principale (per accesso al controller).
            url: URL da aprire nel browser.
        """
        qurl: QUrl = QUrl.fromUserInput(url)
        if not qurl.isValid():
            logger.warning("URL non valido, impossibile aprire nel browser: %r", url)
            return
        logger.debug("Apertura URL nel browser: %s", qurl.toString())
        QDesktopServices.openUrl(qurl)

    @staticmethod
    def search_changed(window: MainWindow, text: str) -> None:
        """Filtra la lista articoli in base al testo."""
        window._news_view.filter_by_text(text)


__all__ = ["MainWindowActions"]
