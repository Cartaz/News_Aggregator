"""Regression coverage for tray counter and QML restore synchronization."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAY_PATH = PROJECT_ROOT / "ui" / "tray.py"
WINDOW_PATH = PROJECT_ROOT / "ui" / "window.py"
MAIN_PATH = PROJECT_ROOT / "main.py"


def test_tray_unread_counter_has_separate_large_orange_digits() -> None:
    source = TRAY_PATH.read_text(encoding="utf-8")
    body = source.split("def set_unread_count", 1)[1].split("def notify_new_items", 1)[0]
    assert "canvas.fill(Qt.GlobalColor.transparent)" in body
    assert "self._base_icon.pixmap(40, 40)" in body
    assert "text_rect = QRect(31, 4, 33, 56)" in body
    assert 'painter.setPen(QColor("#141414"))' in body
    assert 'painter.setPen(QColor("#FF6600"))' in body
    assert "drawEllipse" not in body


def test_window_restore_resyncs_qml_snapshot() -> None:
    source = WINDOW_PATH.read_text(encoding="utf-8")
    assert "QEvent.Type.WindowActivate" in source
    assert "self.ui.sync()" in source
    assert "def restore_from_tray" in source


def test_main_routes_tray_restore_through_single_sync_path() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")
    assert "tray.showWindowRequested.connect(window.restore_from_tray)" in source
    assert "tray.messageClicked.connect(window.restore_from_tray)" in source


def test_close_without_close_to_tray_quits_application() -> None:
    source = WINDOW_PATH.read_text(encoding="utf-8")
    close_block = source.split("QEvent.Type.Close", 1)[1]
    assert "self._controller.settings.close_to_tray" in close_block
    assert "QApplication.quit()" in close_block
