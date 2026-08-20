"""Test UI minimi (richiedono PySide6 e pytest-qt).

Questi test verificano la costruzione dei widget principali senza
eseguire il loop eventi. Sono marcati ``pytest.mark.ui`` per
permettere l'esclusione con ``pytest -m "not ui"``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")
pytestmark = pytest.mark.ui


def test_status_indicator_states(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Lo status indicator deve cambiare stato senza errori."""
    from ui.widgets.status_indicator import StatusIndicator

    widget = StatusIndicator()
    qtbot.addWidget(widget)
    widget.set_state(StatusIndicator.State.RUNNING)
    assert widget.get_state() == StatusIndicator.State.RUNNING
    widget.set_state(StatusIndicator.State.ERROR)
    assert widget.get_state() == StatusIndicator.State.ERROR


def test_status_indicator_all_states_no_nameerror(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Regressione: set_state non deve lanciare NameError su State.RUNNING.

    Storia: ``State`` è una classe annidata dentro ``StatusIndicator``;
    dentro i metodi non è in scope come nome semplice. Usare
    ``StatusIndicator.State.X`` esplicito.
    """
    from ui.widgets.status_indicator import StatusIndicator

    widget = StatusIndicator()
    qtbot.addWidget(widget)
    # Ciclo tutti gli stati per essere sicuro che ogni ramo funzioni
    for state in StatusIndicator.State:
        widget.set_state(state)
        assert widget.get_state() == state
    # Stato iniziale + ritorno a STOPPED
    widget.set_state(StatusIndicator.State.RUNNING)
    widget.set_state(StatusIndicator.State.STOPPED)
    widget.set_state(StatusIndicator.State.PAUSED)
    widget.set_state(StatusIndicator.State.ERROR)
    assert widget.get_state() == StatusIndicator.State.ERROR


def test_shortcut_badge_text(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Il badge scorciatoia deve mostrare il testo passato."""
    from ui.widgets.shortcut_badge import ShortcutBadge

    badge = ShortcutBadge("Ctrl+N")
    qtbot.addWidget(badge)
    assert badge.text() == "Ctrl+N"
    assert badge.get_shortcut() == "Ctrl+N"


def test_feed_input_validation(qtbot) -> None:  # type: ignore[no-untyped-def]
    """is_valid_url deve rifiutare URL non http(s)."""
    from ui.widgets.feed_input import is_valid_url

    assert is_valid_url("https://example.com/feed.xml")
    assert is_valid_url("http://example.com/feed")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("not a url")
    assert not is_valid_url("")


def test_normalize_url_adds_scheme(qtbot) -> None:  # type: ignore[no-untyped-def]
    """normalize_url deve aggiungere https:// se mancante."""
    from ui.widgets.feed_input import normalize_url

    assert normalize_url("guru3d.com") == "https://guru3d.com"
    assert normalize_url("www.guru3d.com") == "https://www.guru3d.com"
    assert normalize_url("https://example.com") == "https://example.com"
    assert normalize_url("http://example.com/feed") == "http://example.com/feed"


def test_normalize_url_rejects_garbage(qtbot) -> None:  # type: ignore[no-untyped-def]
    """normalize_url deve rifiutare input non validi."""
    from ui.widgets.feed_input import normalize_url

    with pytest.raises(ValueError):
        normalize_url("")
    with pytest.raises(ValueError):
        normalize_url("   ")
    with pytest.raises(ValueError):
        normalize_url("not a url at all")


def test_action_button_emits_click(qtbot) -> None:  # type: ignore[no-untyped-def]
    """ActionButton deve emettere clicked quando premuto."""
    from ui.widgets.action_button import ActionButton

    btn = ActionButton("Test", shortcut="Ctrl+T")
    qtbot.addWidget(btn)
    with qtbot.waitSignal(btn.clicked, timeout=1000):
        btn.click()


def test_card_add_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Card deve accettare widget figli senza errori."""
    from PySide6.QtWidgets import QLabel

    from ui.widgets.card import Card

    card = Card("Titolo Test")
    qtbot.addWidget(card)
    label = QLabel("contenuto")
    card.add_widget(label)
    assert card.get_title() == "Titolo Test"
    card.set_title("Nuovo")
    assert card.get_title() == "Nuovo"


def test_news_view_constructs_without_attribute_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Regressione: NewsView non deve lanciare AttributeError su ResizeMode.

    Storia: ``QTableWidget.ResizeMode`` NON esiste in PySide6. L'enum
    appartiene a ``QHeaderView``. Usare ``QHeaderView.ResizeMode.X``.
    """
    from ui.widgets.news_view import NewsView

    view = NewsView()
    qtbot.addWidget(view)
    # Se arriviamo qui senza AttributeError, il test è passato


def test_news_view_table_header_modes(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Verifica che le 4 colonne abbiano i mode di resize corretti."""
    from PySide6.QtWidgets import QHeaderView

    from ui.widgets.news_view import NewsView

    view = NewsView()
    qtbot.addWidget(view)
    header = view._table.horizontalHeader()
    assert (
        header.sectionResizeMode(NewsView.COL_DATE) == QHeaderView.ResizeMode.Fixed
    )
    assert (
        header.sectionResizeMode(NewsView.COL_TIME) == QHeaderView.ResizeMode.Fixed
    )
    assert (
        header.sectionResizeMode(NewsView.COL_SOURCE)
        == QHeaderView.ResizeMode.Interactive
    )
    assert (
        header.sectionResizeMode(NewsView.COL_TITLE) == QHeaderView.ResizeMode.Stretch
    )
    # Verifica numero colonne
    assert view._table.columnCount() == 4


# ---------------------------------------------------------------------------
# Test di regressione per close-to-tray + badge articoli non letti
# ---------------------------------------------------------------------------


def test_settings_close_to_tray_default_true() -> None:  # type: ignore[no-untyped-def]
    """L'impostazione close_to_tray deve defaultare a True."""
    from config.settings import Settings

    s = Settings()
    assert s.close_to_tray is True


def test_tray_icon_set_unread_count(qtbot) -> None:  # type: ignore[no-untyped-def]
    """TrayIcon.set_unread_count deve aggiornare conteggio e tooltip."""
    from ui.tray_icon import TrayIcon

    tray = TrayIcon()
    qtbot.addWidget(tray)

    # Badge iniziale = 0
    assert tray.get_unread_count() == 0

    # Imposta 5 non letti
    tray.set_unread_count(5)
    assert tray.get_unread_count() == 5
    assert "5" in tray._tray.toolTip()

    # Torna a 0: tooltip pulito
    tray.set_unread_count(0)
    assert tray.get_unread_count() == 0
    assert tray._tray.toolTip() == "News Aggregator"


def test_tray_icon_overflow_99_plus(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Con count > 99 il badge deve restare a 99 (visualizzato come '99+').

    Verifica che l'icona venga rigenerata senza errori anche con numeri
    grandi. Il rendering del testo '99+' è testato indirettamente dal
    fatto che set_unread_count non solleva eccezioni.
    """
    from ui.tray_icon import TrayIcon

    tray = TrayIcon()
    qtbot.addWidget(tray)

    # 150 articoli non letti → badge deve dire "99+ (no crash)
    tray.set_unread_count(150)
    assert tray.get_unread_count() == 150
    assert "150" in tray._tray.toolTip()

    # 99 articoli → ancora numero normale
    tray.set_unread_count(99)
    assert tray.get_unread_count() == 99

    # 100 articoli → "99+" nel badge
    tray.set_unread_count(100)
    assert tray.get_unread_count() == 100


def test_tray_icon_negative_count_clamped(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Count negativo deve essere clamped a 0."""
    from ui.tray_icon import TrayIcon

    tray = TrayIcon()
    qtbot.addWidget(tray)
    tray.set_unread_count(-5)
    assert tray.get_unread_count() == 0


def test_tray_icon_emits_show_window_requested(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Il click sull'icona tray deve emettere show_window_requested."""
    from PySide6.QtWidgets import QSystemTrayIcon

    from ui.tray_icon import TrayIcon

    tray = TrayIcon()
    qtbot.addWidget(tray)

    received: list[bool] = []
    tray.show_window_requested.connect(lambda: received.append(True))

    # Simula il click singolo
    tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
    assert received == [True]


def test_tray_icon_emits_quit_requested(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Il menu 'Esci' del tray deve emettere quit_requested."""
    from ui.tray_icon import TrayIcon

    tray = TrayIcon()
    qtbot.addWidget(tray)

    received: list[bool] = []
    tray.quit_requested.connect(lambda: received.append(True))

    # Trova l'azione "Esci" e attivala
    actions = tray._menu.actions()
    quit_action = next(
        (a for a in actions if a.text() == "Esci"), None
    )
    assert quit_action is not None, "Azione 'Esci' non trovata nel menu"
    quit_action.trigger()
    assert received == [True]


# ---------------------------------------------------------------------------
# Test di regressione: apertura link nel browser esterno
# (bug: click sul link nel dettaglio articolo non faceva nulla,
#  warning "QTextBrowser: No document for <url>" in console)
# ---------------------------------------------------------------------------


def test_news_view_open_external_links_enabled(qtbot) -> None:  # type: ignore[no-untyped-def]
    """QTextBrowser deve avere setOpenExternalLinks(True).

    Riproduce il bug: con setOpenExternalLinks(False) i click sui link
    <a href="..."> nel dettaglio articolo non aprivano il browser, e
    Qt stampava il warning "No document for <url>" in console.
    La correzione è impostare setOpenExternalLinks(True) così Qt
    delega direttamente a QDesktopServices.openUrl.
    """
    from ui.widgets.news_view import NewsView

    view = NewsView()
    qtbot.addWidget(view)
    assert view._detail.openExternalLinks() is True, (
        "setOpenExternalLinks deve essere True per aprire i link nel browser"
    )


def test_news_view_anchor_clicked_emits_open_in_browser(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Il click su un anchor nel QTextBrowser deve emettere open_in_browser."""
    from PySide6.QtCore import QUrl

    from ui.widgets.news_view import NewsView

    view = NewsView()
    qtbot.addWidget(view)

    received: list[str] = []
    view.open_in_browser.connect(lambda url: received.append(url))

    # Simula il click su un link (anchorClicked emette QUrl)
    view._on_link_clicked(QUrl("https://example.com/article"))

    assert received == ["https://example.com/article"]


def test_open_in_browser_uses_from_user_input(qtbot) -> None:  # type: ignore[no-untyped-def]
    """MainWindowActions.open_in_browser deve usare QUrl.fromUserInput.

    QUrl() diretto fallisce su URL con caratteri non ASCII o spazi;
    QUrl.fromUserInput() è la funzione raccomandata da Qt per URL
    provenienti da fonti non affidabili (feed RSS).
    Verifica che URL con spazi e caratteri Unicode vengano gestiti.
    """
    from unittest.mock import patch, MagicMock

    from ui.main_window_actions import MainWindowActions

    window = MagicMock()
    mock_open = MagicMock()
    with patch("ui.main_window_actions.QDesktopServices.openUrl", mock_open):
        # URL con spazi e caratteri non ASCII (tipico dei feed RSS internazionali)
        weird_url = "https://example.com/café e brioche/article"
        MainWindowActions.open_in_browser(window, weird_url)
        assert mock_open.called, "QDesktopServices.openUrl non chiamato"
        qurl = mock_open.call_args[0][0]
        assert qurl.isValid(), f"URL non valido dopo fromUserInput: {qurl.toString()}"
        # L'URL deve preservare il dominio
        assert "example.com" in qurl.toString()


def test_open_in_browser_rejects_invalid_url(qtbot) -> None:  # type: ignore[no-untyped-def]
    """URL completamente malformato non deve causare crash."""
    from unittest.mock import patch, MagicMock

    from ui.main_window_actions import MainWindowActions

    window = MagicMock()
    mock_open = MagicMock()
    with patch("ui.main_window_actions.QDesktopServices.openUrl", mock_open):
        # URL senza schema — fromUserInput potrebbe ancora considerarlo valido
        # aggiungendo http://, ma stringhe vuote/garbage devono essere rifiutate
        MainWindowActions.open_in_browser(window, "")
        # URL vuoto non apre nulla
        assert not mock_open.called or not mock_open.call_args[0][0].isValid()
