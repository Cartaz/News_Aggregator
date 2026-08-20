"""Finestra principale dell'applicazione News Aggregator.

Layout:
- Riga azioni: input URL + "Aggiungi feed" + "Aggiorna tutti"
  + "Elimina feed" sulla stessa riga (compatta, massimizza spazio verticale)
- Ricerca testuale (filtra articoli)
- Centro: splitter orizzontale [SourceList | NewsView]
- Footer: status bar con indicatore di stato animato + messaggi

La finestra rispetta il tema Neumorphism via QSS globale. Le
scorciatoie da tastiera sono registrate tramite ``QShortcut``. La
chiusura avviene tramite pulsante X, Ctrl+Q, o voce menu tray. Le
azioni utente e gli handler degli eventi EventBus sono delegati a
moduli separati (``main_window_actions``, ``main_window_handlers``)
per rispettare il limite di 300 righe per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStatusBar,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from config.constants import Shortcuts, UIConstraints
from config.theme import ThemeSpacing
from core.app_controller import AppController
from core.exceptions import FeedError
from core.models import FeedSource
from ui.event_bridge import EventBridge
from ui.main_window_actions import MainWindowActions
from ui.main_window_handlers import MainWindowHandlers
from ui.widgets.action_button import ActionButton
from ui.widgets.feed_input import FeedInput
from ui.widgets.news_view import NewsView
from ui.widgets.neumorphic_controls import NeumorphicLineEdit
from ui.widgets.source_list import SourceList
from ui.widgets.status_indicator import StatusIndicator

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Finestra principale dell'applicazione.

    Args:
        controller: AppController da usare (iniettato per testabilità).
        parent: Widget genitore.

    Signals:
        quit_requested: Emesso quando l'utente chiude la finestra.
        refresh_single_done: Cross-thread — emesso dal worker thread,
            ricevuto nel main thread per marshallare i callback
            ``on_done`` di ``refresh_feed_async``.
        refresh_all_done: Cross-thread — emesso dal worker thread,
            ricevuto nel main thread per marshallare i callback
            ``on_done`` di ``refresh_all_async``.
    """

    quit_requested = Signal()
    refresh_single_done = Signal(str, bool, str)
    refresh_all_done = Signal(dict)

    def __init__(
        self,
        controller: AppController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller: AppController = controller
        self._bridge: EventBridge = EventBridge(self)
        # Flag per distinguere "chiudi con X" (nascondi se close_to_tray)
        # da "Esci sul serio" (Ctrl+Q, "Esci" dal menu tray). Viene
        # impostato a True prima di chiamare self.close() quando l'utente
        # vuole uscire davvero. handle_close_event lo controlla.
        self._force_quit_requested: bool = False
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._subscribe_events()
        self._setup_refresh_dispatcher()
        self._load_initial_state()

    def _setup_window(self) -> None:
        """Imposta geometria e titolo della finestra."""
        self.setWindowTitle("News Aggregator")
        self.setMinimumSize(
            UIConstraints.WINDOW_MIN_WIDTH,
            UIConstraints.WINDOW_MIN_HEIGHT,
        )
        s = self._controller.settings
        self.resize(s.window_width, s.window_height)

    def _build_ui(self) -> None:
        """Costruisce la struttura visiva della finestra.

        La riga superiore contiene sulla stessa riga: input URL +
        "Aggiungi feed" + "Aggiorna tutti" + "Elimina feed". Questo
        massimizza lo spazio verticale per la vista articoli.
        Il layout usa padding generosi per dare respiro alle ombre
        neumorphic di pulsanti e campi.
        """
        central: QWidget = QWidget(self)
        root: QVBoxLayout = QVBoxLayout(central)
        root.setContentsMargins(
            ThemeSpacing.LG, ThemeSpacing.LG,
            ThemeSpacing.LG, ThemeSpacing.LG,
        )
        root.setSpacing(ThemeSpacing.MD)

        # --- Riga azioni unificata (input + 2 pulsanti sulla stessa riga) ---
        action_bar: QWidget = QWidget(central)
        bar_layout: QHBoxLayout = QHBoxLayout(action_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(ThemeSpacing.SM)

        self._feed_input: FeedInput = FeedInput(action_bar)
        bar_layout.addWidget(self._feed_input, stretch=1)

        # Separatore verticale sottile tra input e azioni globali
        sep: QFrame = QFrame(action_bar)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(2)
        bar_layout.addWidget(sep)

        self._refresh_all_btn: ActionButton = ActionButton(
            label="Aggiorna tutti",
            shortcut=Shortcuts.REFRESH_ALL,
            parent=action_bar,
        )
        bar_layout.addWidget(self._refresh_all_btn)

        self._remove_btn: ActionButton = ActionButton(
            label="Elimina feed",
            shortcut=Shortcuts.REMOVE_FEED,
            danger=True,
            parent=action_bar,
        )
        bar_layout.addWidget(self._remove_btn)

        root.addWidget(action_bar)

        # --- Campo di ricerca articoli ---
        self._search_edit: QLineEdit = NeumorphicLineEdit(central)
        self._search_edit.setPlaceholderText(
            "Filtra articoli per testo… (Ctrl+F)"
        )
        self._search_edit.setClearButtonEnabled(True)
        root.addWidget(self._search_edit)

        # Splitter ridimensionabile tra sorgenti e vista articoli (vincolo #2)
        from PySide6.QtWidgets import QSplitter
        from PySide6.QtCore import Qt as _Qt

        splitter: QSplitter = QSplitter(_Qt.Orientation.Horizontal, central)
        splitter.setChildrenCollapsible(False)
        self._source_list: SourceList = SourceList(splitter)
        # Larghezza minima più generosa per evitare troncamento del testo
        # "Tutti gli articoli" e dei nomi delle sorgenti più lunghi.
        self._source_list.setMinimumWidth(240)
        self._news_view: NewsView = NewsView(splitter)
        splitter.addWidget(self._source_list)
        splitter.addWidget(self._news_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        # Sizes iniziali più generosi per la sidebar (320px invece di 260)
        # per garantire che la colonna "Sorgente" mostri il testo completo
        # senza troncamento e la colonna "Da leggere" abbia spazio sufficiente.
        splitter.setSizes([320, 940])
        # Salva il riferimento per persistere le dimensioni
        self._center_splitter: QSplitter = splitter
        root.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)
        self._build_status_bar()

    def _build_status_bar(self) -> None:
        """Costruisce la status bar con indicatore di stato."""
        status: QStatusBar = QStatusBar(self)
        self.setStatusBar(status)
        self._status_indicator: StatusIndicator = StatusIndicator(status)
        self._status_label: QLabel = QLabel("Pronto", status)
        status.addWidget(self._status_indicator)
        status.addWidget(self._status_label, stretch=1)

    def _connect_signals(self) -> None:
        """Collega i segnali dei widget figli alle azioni utente."""
        a = MainWindowActions
        self._feed_input.feed_submitted.connect(
            lambda url: a.add_feed(self, url)
        )
        self._refresh_all_btn.clicked.connect(
            lambda: a.refresh_all(self)
        )
        self._remove_btn.clicked.connect(lambda: a.remove_feed(self))
        self._source_list.all_selected.connect(
            lambda: a.all_selected(self)
        )
        self._source_list.category_selected.connect(
            lambda cat: a.category_selected(self, cat)
        )
        self._source_list.source_selected.connect(
            lambda sid: a.source_selected(self, sid)
        )
        self._source_list.refresh_requested.connect(
            lambda sid: a.refresh_single_by_id(self, sid)
        )
        self._source_list.remove_requested.connect(
            lambda sid: a.remove_by_id(self, sid)
        )
        self._source_list.rename_requested.connect(
            lambda sid, title: a.rename_feed(self, sid, title)
        )
        self._source_list.category_change_requested.connect(
            lambda sid, cat: a.change_category(self, sid, cat)
        )
        self._news_view.item_activated.connect(
            lambda sid, iid: a.item_activated(self, sid, iid)
        )
        self._news_view.open_in_browser.connect(
            lambda url: a.open_in_browser(self, url)
        )
        self._search_edit.textChanged.connect(
            lambda text: a.search_changed(self, text)
        )

        # Ctrl+Q deve USCIRE davvero dall'app, anche con close_to_tray=True.
        # Impostiamo un flag che handle_close_event controlla per distinguere
        # "l'utente ha richiesto di uscire" (Ctrl+Q / "Esci" dal tray) dal
        # "l'utente ha chiuso la finestra con la X" (deve solo nascondere).
        def _force_quit() -> None:
            self._force_quit_requested = True
            self.close()

        QShortcut(QKeySequence(Shortcuts.QUIT), self, activated=_force_quit)
        QShortcut(
            QKeySequence(Shortcuts.SEARCH), self,
            activated=self._search_edit.setFocus,
        )

    def _subscribe_events(self) -> None:
        """Iscrive gli handler Qt-safe agli eventi del bus."""
        from ui.main_window_init import subscribe_events

        subscribe_events(self)

    def _load_initial_state(self) -> None:
        """Carica feed e categorie dal controller all'avvio."""
        from ui.main_window_init import load_initial_state

        load_initial_state(self)

    def _setup_refresh_dispatcher(self) -> None:
        """Instanzia il dispatcher cross-thread e connette i segnali.

        I callback ``on_done`` di ``refresh_*_async`` girano nel worker
        thread; il dispatcher (con i suoi slot bound) riceve i segnali
        ``refresh_*_done`` e Qt marshalla le chiamate al main thread.
        """
        from ui.main_window_refresh_bridge import RefreshDoneDispatcher

        self._refresh_dispatcher: RefreshDoneDispatcher = RefreshDoneDispatcher(self)
        self.refresh_single_done.connect(
            self._refresh_dispatcher.on_refresh_single_done_qt
        )
        self.refresh_all_done.connect(
            self._refresh_dispatcher.on_refresh_all_done_qt
        )

    # --- Metodi interni usati da Actions e Handlers ---

    def _refresh_news_view(self, source_id: str | None) -> None:
        """Backward-compat: come _refresh_news_view_by_source."""
        from ui.news_view_refresher import refresh_by_source

        refresh_by_source(self, source_id)

    def _refresh_news_view_by_source(self, source_id: str | None) -> None:
        """Aggiorna la vista articoli per la sorgente indicata."""
        from ui.news_view_refresher import refresh_by_source

        refresh_by_source(self, source_id)

    def _refresh_news_view_all(self) -> None:
        """Mostra il mega-feed con tutti gli articoli di tutte le sorgenti."""
        from ui.news_view_refresher import refresh_all

        refresh_all(self)

    def _refresh_news_view_by_category(self, category: str) -> None:
        """Mostra gli articoli aggregati di una categoria."""
        from ui.news_view_refresher import refresh_by_category

        refresh_by_category(self, category)

    def _refresh_tray_badge(self) -> None:
        """Aggiorna il badge della tray icon con il totale articoli non letti.

        Ricalcola il numero totale di articoli non letti su TUTTI i feed
        (esclusi quelli potati per età) e lo propaga alla tray icon che
        ridisegna il badge numerico sovrapposto all'icona.

        Chiamato da ``MainWindowHandlers`` ogni volta che lo stato degli
        articoli cambia: refresh completato, articolo marcato come letto,
        feed aggiunto/rimosso.
        """
        tray = getattr(self, "_tray", None)
        if tray is None or not hasattr(tray, "set_unread_count"):
            return
        try:
            count: int = self._controller.get_total_unread_count()
        except Exception as exc:
            logger.debug("Impossibile calcolare unread count: %s", exc)
            return
        tray.set_unread_count(count)

    def _set_status(
        self, message: str, state: StatusIndicator.State
    ) -> None:
        """Aggiorna il messaggio e l'indicatore di stato."""
        self._status_label.setText(message)
        self._status_indicator.set_state(state)

    def tray_show_message(self, title: str, body: str) -> None:
        """Inoltra una notifica alla tray icon (se presente)."""
        tray = getattr(self, "_tray", None)
        if tray is not None and hasattr(tray, "show_message"):
            tray.show_message(title, body)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Gestisce la chiusura: salva geometria, ferma worker, propaga."""
        from ui.main_window_close import handle_close_event

        handle_close_event(self, event)


__all__ = ["MainWindow"]
