"""Regression contract for automatic UI/backend resynchronization."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_JS = PROJECT_ROOT / "ui" / "web" / "app.js"


def test_ui_polls_backend_even_when_refresh_signals_are_missed() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "async function pollBackendState()" in source
    assert "function articleStateFingerprint(snapshot)" in source
    assert "window.setInterval(() => { void pollBackendState(); }, 1000);" in source
    assert "window.addEventListener('focus', () => { void pollBackendState(); });" in source
    assert "visibilitychange" in source
    assert "nextOperationId > previousOperationId" in source
    assert "const articlesChanged = articleStateFingerprint(nextSnapshot) !== previousArticleState;" in source
    assert "await loadItems({ syncSnapshot: false });" in source
    assert "startBackendHeartbeat();" in source
