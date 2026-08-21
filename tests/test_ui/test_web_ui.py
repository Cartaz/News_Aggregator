"""Static and bridge-level regression tests for the HTML desktop UI."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "ui" / "web"


def test_web_assets_exist() -> None:
    assert (WEB_ROOT / "index.html").is_file()
    assert (WEB_ROOT / "styles.css").is_file()
    assert (WEB_ROOT / "log-viewer.css").is_file()
    for name in ("state.js", "articles.js", "dialogs.js", "app.js"):
        assert (WEB_ROOT / name).is_file()


def test_surface_and_accent_are_exact() -> None:
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    assert "--surface: rgb(20, 20, 20);" in css
    assert "--accent: rgb(255, 102, 0);" in css
    assert "--text-primary: rgb(225, 225, 225);" in css
    assert "--text-secondary: rgb(135, 135, 135);" in css
    assert "--text-muted: rgb(90, 90, 90);" in css


def test_no_surface_gradients_or_forbidden_card_colors() -> None:
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8").lower()
    assert "linear-gradient" not in css
    assert "radial-gradient" not in css
    for forbidden in ("#181818", "#1a1a1a", "#202020", "#242424"):
        assert forbidden not in css


def test_required_neumorphic_shadows_and_accessibility() -> None:
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "--shadow-raised:" in css
    assert "--shadow-inset:" in css
    assert "--shadow-active-inset-glow:" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    for tag in ("<button", "<input", "<label", "<nav", "<main", "<section", "<header"):
        assert tag in html


def test_qwebchannel_is_local_and_no_frontend_framework() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8").lower()
    assert "qrc:///qtwebchannel/qwebchannel.js" in html
    for framework in ("react", "vue", "angular", "bootstrap", "tailwind"):
        assert framework not in html


def test_bridge_normalizes_user_urls() -> None:
    pytest.importorskip("PySide6")
    from ui.bridge import WebBridge

    assert WebBridge._normalize_url("example.com") == "https://example.com"
    assert WebBridge._normalize_url("https://example.com/feed.xml") == "https://example.com/feed.xml"
    with pytest.raises(ValueError):
        WebBridge._normalize_url("ftp://example.com/feed")
    with pytest.raises(ValueError):
        WebBridge._normalize_url("")
