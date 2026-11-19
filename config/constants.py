"""Costanti globali dell'applicazione News Aggregator.

Definisce metadati dell'app, valori predefiniti per i feed, vincoli UI
e percorsi XDG calcolati dinamicamente. Nessun modulo di questa classe
importa da altri livelli applicativi: è puramente dichiarativo.
"""

from __future__ import annotations

import os
from pathlib import Path


class AppMeta:
    """Metadati identificativi dell'applicazione."""

    NAME = "news-aggregator"
    DISPLAY_NAME = "News Aggregator"
    VERSION = "1.1.0"
    LICENSE = "GPL-3.0-or-later"


class Paths:
    """Percorsi XDG calcolati dinamicamente."""

    HOME: Path = Path.home()

    CONFIG_HOME: Path = Path(
        os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config"))
    )

    DATA_HOME: Path = Path(
        os.environ.get("XDG_DATA_HOME", str(HOME / ".local" / "share"))
    )

    STATE_HOME: Path = Path(
        os.environ.get("XDG_STATE_HOME", str(HOME / ".local" / "state"))
    )

    APP_CONFIG_DIR: Path = CONFIG_HOME / AppMeta.NAME
    APP_DATA_DIR: Path = DATA_HOME / AppMeta.NAME
    APP_STATE_DIR: Path = STATE_HOME / AppMeta.NAME
    SITE_ICON_CACHE_DIR: Path = APP_DATA_DIR / "site-icons"

    SETTINGS_FILE: Path = APP_CONFIG_DIR / "settings.json"
    FEEDS_FILE: Path = APP_DATA_DIR / "feeds.json"
    LOG_FILE: Path = APP_STATE_DIR / "app.log"

    ASSETS_DIR: Path = Path(__file__).resolve().parent.parent / "assets"
    ICONS_DIR: Path = ASSETS_DIR / "icons"
    APP_ICON: Path = ICONS_DIR / f"{AppMeta.NAME}.svg"

    @classmethod
    def ensure_user_dirs(cls) -> None:
        """Crea le directory utente XDG se mancanti."""
        for path in (
            cls.APP_CONFIG_DIR,
            cls.APP_DATA_DIR,
            cls.APP_STATE_DIR,
            cls.SITE_ICON_CACHE_DIR,
        ):
            path.mkdir(parents=True, exist_ok=True)


class FeedDefaults:
    """Valori predefiniti per il recupero e la gestione dei feed."""

    MAX_ITEMS_PER_FEED: int = 50
    MAX_SUPPORTED_ITEMS_PER_FEED: int = 500
    REQUEST_TIMEOUT_SECONDS: int = 15
    # Numero massimo di feed aggiornati contemporaneamente. Un limite basso
    # riduce sensibilmente la latenza globale senza martellare i server RSS.
    REFRESH_MAX_WORKERS: int = 4
    # User-Agent: molti siti (TechPowerUp, ecc.) bloccano i reader RSS
    # noti. Usiamo un UA browser-like puro senza identificare l'app
    # come RSS reader, così passiamo i WAF basilari. Siti con bot
    # detection avanzata (Cloudflare JS challenge) richiedono comunque
    # l'URL del feed diretto invece della homepage.
    USER_AGENT: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    MAX_SUMMARY_LENGTH: int = 800
    MAX_ITEM_AGE_HOURS: int = 48


class UIConstraints:
    """Vincoli dimensionali e di layout dell'interfaccia."""

    WINDOW_MIN_WIDTH: int = 900
    WINDOW_MIN_HEIGHT: int = 600
    WINDOW_DEFAULT_WIDTH: int = 1280
    WINDOW_DEFAULT_HEIGHT: int = 800
    WINDOW_MAX_DIMENSION: int = 32768

    SOURCE_LIST_MIN_WIDTH: int = 240
    SOURCE_LIST_MAX_WIDTH: int = 480
