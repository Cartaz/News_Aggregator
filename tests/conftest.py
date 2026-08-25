"""Fixture condivise per i test."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Assicura che la root del progetto sia nel path
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige i percorsi XDG su una directory temporanea.

    Args:
        tmp_path: Fixture pytest per directory temporanea.
        monkeypatch: Fixture pytest per patchare env vars.

    Returns:
        Path della directory temporanea root.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    from config import constants

    monkeypatch.setattr(
        constants.Paths,
        "CONFIG_HOME",
        tmp_path / "config",
    )
    monkeypatch.setattr(
        constants.Paths,
        "DATA_HOME",
        tmp_path / "data",
    )
    monkeypatch.setattr(
        constants.Paths,
        "STATE_HOME",
        tmp_path / "state",
    )
    monkeypatch.setattr(
        constants.Paths,
        "APP_CONFIG_DIR",
        tmp_path / "config" / "news-aggregator",
    )
    monkeypatch.setattr(
        constants.Paths,
        "APP_DATA_DIR",
        tmp_path / "data" / "news-aggregator",
    )
    monkeypatch.setattr(
        constants.Paths,
        "APP_STATE_DIR",
        tmp_path / "state" / "news-aggregator",
    )
    monkeypatch.setattr(
        constants.Paths,
        "SETTINGS_FILE",
        tmp_path / "config" / "news-aggregator" / "settings.json",
    )
    monkeypatch.setattr(
        constants.Paths,
        "FEEDS_FILE",
        tmp_path / "data" / "news-aggregator" / "feeds.json",
    )
    monkeypatch.setattr(
        constants.Paths,
        "LOG_FILE",
        tmp_path / "state" / "news-aggregator" / "app.log",
    )
    return tmp_path


@pytest.fixture
def sample_rss_bytes() -> bytes:
    """Restituisce un feed RSS 2.0 di esempio come bytes.

    Le date sono calcolate dinamicamente per essere entro la finestra
    di 48 ore (vincolo FeedDefaults.MAX_ITEM_AGE_HOURS), così i test
    che verificano il pruning non eliminano gli articoli di default.
    """
    from datetime import datetime, timedelta, timezone

    now: datetime = datetime.now(timezone.utc)
    date1: datetime = now - timedelta(hours=2)
    date2: datetime = now - timedelta(hours=1)
    rfc_date1: str = date1.strftime("%a, %d %b %Y %H:%M:%S +0000")
    rfc_date2: str = date2.strftime("%a, %d %b %Y %H:%M:%S +0000")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Feed di Prova</title>
    <link>https://example.com</link>
    <description>Feed di test</description>
    <item>
      <title>Primo articolo</title>
      <link>https://example.com/1</link>
      <description>&lt;p&gt;Testo con &lt;b&gt;HTML&lt;/b&gt; da pulire.&lt;/p&gt;</description>
      <pubDate>{rfc_date1}</pubDate>
      <author>Autore 1</author>
    </item>
    <item>
      <title>Secondo articolo</title>
      <link>https://example.com/2</link>
      <description>Testo semplice senza HTML.</description>
      <pubDate>{rfc_date2}</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")
