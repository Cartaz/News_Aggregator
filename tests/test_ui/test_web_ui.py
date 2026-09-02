"""Static and bridge-level regression tests for the HTML desktop UI."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "ui" / "web"
BRIDGE_PATH = PROJECT_ROOT / "ui" / "bridge.py"
CONTROLLER_PATH = PROJECT_ROOT / "core" / "app_controller.py"


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


def test_radius_hierarchy_is_the_only_non_circular_radius_system() -> None:
    css = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (WEB_ROOT / "styles.css", WEB_ROOT / "log-viewer.css")
    )
    assert "--radius-xl: 28px;" in css
    assert "--radius-lg: 22px;" in css
    assert "--radius-md: 16px;" in css
    assert "--radius-sm: 12px;" in css

    allowed = {
        "var(--radius-xl)",
        "var(--radius-lg)",
        "var(--radius-md)",
        "var(--radius-sm)",
        "50%",
    }
    declarations = re.findall(r"border-radius:\s*([^;]+);", css)
    assert declarations
    assert set(declarations) <= allowed


def test_selected_article_uses_accent_and_inset_glow() -> None:
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    assert (
        ".article-row.selected { border-radius: var(--radius-sm); color: var(--accent); "
        "box-shadow: var(--shadow-active-inset-glow); border-top-color: transparent; }"
    ) in css


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


def test_refresh_ui_uses_controller_snapshot_as_single_source() -> None:
    state_js = (WEB_ROOT / "state.js").read_text(encoding="utf-8")
    articles_js = (WEB_ROOT / "articles.js").read_text(encoding="utf-8")
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    bridge_py = BRIDGE_PATH.read_text(encoding="utf-8")
    controller_py = CONTROLLER_PATH.read_text(encoding="utf-8")

    assert '"refreshing": self._controller.get_refresh_state()' in bridge_py
    assert "self._refreshing_all" not in bridge_py
    assert "self._refresh_current" not in bridge_py
    assert "self._refresh_total" not in bridge_py
    assert "self._refreshing_feeds" not in bridge_py
    assert "QTimer.singleShot" not in bridge_py

    assert "self._refresh_state = RefreshState()" in controller_py
    assert "def get_refresh_state(" in controller_py
    assert 'self._emit_event("refresh_state_changed"' in controller_py

    assert "const backendBusy = Boolean(refreshState.active);" in state_js
    assert "updateRefreshProgress(refreshState);" in state_js
    assert "scheduleRefreshStatePoll" not in state_js
    assert "state.refresh" not in state_js

    assert "function updateRefreshProgress(refreshState = state.snapshot?.refreshing)" in articles_js
    assert "Number(refreshState.current)" in articles_js
    assert "Number(refreshState.total)" in articles_js
    assert "state.refresh" not in articles_js

    assert "state.backend.stateChanged.connect" in app_js
    assert "state.backend.refreshFinished.connect" in app_js
    assert "state.backend.uiSyncRequested.connect" in app_js
    assert "state.backend.refreshProgress.connect" not in app_js
    assert "setInterval" not in app_js


def test_segmented_refresh_progress_keeps_presentation_in_css() -> None:
    articles_js = (WEB_ROOT / "articles.js").read_text(encoding="utf-8")
    css = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

    assert "function ensureRefreshSegments(total)" in articles_js
    assert "segment.className = 'refresh-segment';" in articles_js
    assert "segment.classList.toggle('done', index < completed);" in articles_js
    assert "fill.classList.toggle('single', total <= 1);" in articles_js
    assert ".refresh-segment {" in css
    assert ".refresh-segment.done {" in css
    assert ".refresh-fill.single { gap: 0; }" in css
    assert "segment.style" not in articles_js
    assert "fill.style" not in articles_js
    assert "track.style" not in articles_js
    assert "rgba(255,102,0" not in articles_js


def test_arrow_keys_navigate_filtered_articles_safely() -> None:
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "function canNavigateArticlesWithArrows(target)" in app_js
    assert "async function navigateArticleSelection(direction)" in app_js
    assert "const items = state.filteredItems;" in app_js
    assert "event.key === 'ArrowUp' || event.key === 'ArrowDown'" in app_js
    assert "void navigateArticleSelection(event.key === 'ArrowDown' ? 1 : -1);" in app_js
    assert "target.matches('input, textarea, select')" in app_js
    assert "target.isContentEditable" in app_js
    assert "selectedRow.scrollIntoView({ block: 'nearest', behavior: 'auto' });" in app_js


def test_bridge_normalizes_user_urls() -> None:
    pytest.importorskip("PySide6")
    from ui.bridge import WebBridge

    assert WebBridge._normalize_url("example.com") == "https://example.com"
    assert WebBridge._normalize_url("https://example.com/feed.xml") == "https://example.com/feed.xml"
    with pytest.raises(ValueError):
        WebBridge._normalize_url("ftp://example.com/feed")
    with pytest.raises(ValueError):
        WebBridge._normalize_url("")


def test_bridge_returns_actual_native_open_result() -> None:
    pytest.importorskip("PySide6")
    from ui.bridge import WebBridge

    class ControllerStub:
        def register_event_listener(self, listener) -> None:  # type: ignore[no-untyped-def]
            self.listener = listener

    opened: list[str] = []

    def failing_open(url: str) -> tuple[bool, str]:
        opened.append(url)
        return False, "browser unavailable"

    bridge = WebBridge(ControllerStub(), open_external=failing_open)  # type: ignore[arg-type]
    result = json.loads(bridge.openExternal("example.com"))

    assert opened == ["https://example.com"]
    assert result["ok"] is False
    assert result["message"] == "browser unavailable"


def test_bridge_returns_success_only_after_native_open_succeeds() -> None:
    pytest.importorskip("PySide6")
    from ui.bridge import WebBridge

    class ControllerStub:
        def register_event_listener(self, listener) -> None:  # type: ignore[no-untyped-def]
            self.listener = listener

    bridge = WebBridge(  # type: ignore[arg-type]
        ControllerStub(),
        open_external=lambda url: (True, "Link aperto"),
    )
    result = json.loads(bridge.openExternal("https://example.com"))

    assert result["ok"] is True
    assert result["message"] == "Link aperto"
