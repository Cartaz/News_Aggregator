"""Regression coverage for unread counter presentation."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAY_PATH = PROJECT_ROOT / "ui" / "tray.py"
STYLES_PATH = PROJECT_ROOT / "ui" / "web" / "styles.css"


def test_tray_unread_counter_is_plain_orange_text() -> None:
    source = TRAY_PATH.read_text(encoding="utf-8")
    body = source.split("def set_unread_count", 1)[1].split("def notify_new_items", 1)[0]

    assert 'painter.setPen(QColor("#FF6600"))' in body
    assert "font.setPixelSize(28)" in body
    assert "painter.drawText(31, 31, 33, 33" in body
    assert "drawEllipse" not in body
    assert "setBrush" not in body


def test_main_window_unread_badges_keep_neumorphic_capsule() -> None:
    css = STYLES_PATH.read_text(encoding="utf-8")

    assert ".count-badge { min-width: 24px; height: 23px;" in css
    assert "border-radius: 10px;" in css
    assert "background: var(--surface); box-shadow: var(--shadow-inset-small);" in css
    assert ".source-row.selected .count-badge { color: var(--accent); }" in css
