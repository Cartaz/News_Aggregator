"""Regression contract for signal-driven UI/backend synchronization."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_JS = PROJECT_ROOT / "ui" / "web" / "app.js"
STATE_JS = PROJECT_ROOT / "ui" / "web" / "state.js"


def test_ui_uses_webchannel_signals_without_background_polling() -> None:
    app_source = APP_JS.read_text(encoding="utf-8")
    state_source = STATE_JS.read_text(encoding="utf-8")

    assert "state.backend.stateChanged.connect" in app_source
    assert "state.backend.refreshFinished.connect" in app_source
    assert "state.backend.uiSyncRequested.connect" in app_source
    assert "syncItemsAfterCompletedRefresh" in app_source
    assert "resyncVisibleView" in app_source

    assert "pollBackendState" not in app_source
    assert "startBackendHeartbeat" not in app_source
    assert "setInterval" not in app_source
    assert "scheduleRefreshStatePoll" not in state_source
    assert "refreshPollTimer" not in state_source
    assert "setTimeout(async () =>" not in state_source
