"""Regression coverage for unread counter presentation and tray resume sync."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAY_PATH = PROJECT_ROOT / "ui" / "tray.py"
STYLES_PATH = PROJECT_ROOT / "ui" / "web" / "styles.css"
WINDOW_PATH = PROJECT_ROOT / "ui" / "window.py"
APP_JS_PATH = PROJECT_ROOT / "ui" / "web" / "app.js"


def test_tray_unread_counter_has_separate_large_orange_digits() -> None:
    source = TRAY_PATH.read_text(encoding="utf-8")
    body = source.split("def set_unread_count", 1)[1].split("def notify_new_items", 1)[0]

    assert "canvas.fill(Qt.GlobalColor.transparent)" in body
    assert "self._base_icon.pixmap(40, 40)" in body
    assert "painter.drawPixmap(0, 12, base_pixmap)" in body
    assert "text_rect = QRect(31, 4, 33, 56)" in body
    assert 'painter.setPen(QColor("#141414"))' in body
    assert 'painter.setPen(QColor("#FF6600"))' in body
    assert "font.setPixelSize(36)" in body
    assert "QFontMetrics(font)" in body
    assert "drawEllipse" not in body
    assert "setBrush" not in body


def test_main_window_unread_badges_keep_neumorphic_capsule() -> None:
    css = STYLES_PATH.read_text(encoding="utf-8")

    assert ".count-badge { min-width: 24px; height: 23px;" in css
    assert "border-radius: var(--radius-sm);" in css
    assert "background: var(--surface); box-shadow: var(--shadow-inset-small);" in css
    assert ".source-row.selected .count-badge { color: var(--accent); }" in css


def test_window_restore_requests_full_webview_resync() -> None:
    window_source = WINDOW_PATH.read_text(encoding="utf-8")
    app_source = APP_JS_PATH.read_text(encoding="utf-8")

    assert "self._ui_sync_timer = QTimer(self)" in window_source
    assert "self._ui_sync_timer.timeout.connect(self.bridge.request_ui_sync)" in window_source
    assert "event.type() == QEvent.Type.WindowActivate" in window_source
    assert "def showEvent(self, event: QShowEvent)" in window_source
    assert "def restore_from_tray(self)" in window_source
    assert "self._schedule_ui_sync()" in window_source
    assert "state.backend.uiSyncRequested.connect" in app_source
    assert "async function resyncVisibleView()" in app_source
    assert "await loadItems({ syncSnapshot: false });" in app_source
