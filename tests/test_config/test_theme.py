"""Test per config/theme.py e config/constants.py."""

from __future__ import annotations

from config.constants import AppMeta, FeedDefaults, Paths, Shortcuts, UIConstraints
from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


def test_app_meta_basic() -> None:
    """AppMeta deve avere nome e versione non vuoti."""
    assert AppMeta.NAME
    assert AppMeta.VERSION
    assert AppMeta.DISPLAY_NAME


def test_theme_colors_primary_is_neumorphism_accent() -> None:
    """Il colore PRIMARY deve essere l'arancione Neumorphism (#ff6600).

    Aggiornato da Breeze Dark (teal) a Neumorphism (arancione) per
    allineamento alle nuove linee guida UI.
    """
    primary: str = ThemeColors.PRIMARY.lower()
    assert primary == "#ff6600"


def test_theme_colors_danger_is_neumorphism_bad() -> None:
    """Il colore DANGER deve essere il rosso "bad" Neumorphism (#e56a65)."""
    danger: str = ThemeColors.DANGER.lower()
    assert danger == "#e56a65"


def test_theme_colors_shadows_defined() -> None:
    """I token ombra Neumorphism devono essere presenti e corretti."""
    # Ombra chiara (alto/sinistra) — più chiara del background
    assert ThemeColors.SHADOW_LIGHT.lower() == "#1e1e21"
    # Ombra scura (basso/destra) — nero puro
    assert ThemeColors.SHADOW_DARK.lower() == "#000000"
    # Background e card coincidono (un unico materiale)
    assert ThemeColors.BG_MAIN.lower() == "#121213"
    assert ThemeColors.BG_CARD.lower() == ThemeColors.BG_MAIN.lower()
    assert ThemeColors.BG_INPUT.lower() == ThemeColors.BG_MAIN.lower()


def test_theme_colors_text_primary_high_contrast() -> None:
    """TEXT_PRIMARY deve essere molto chiaro per contrasto su #121213."""
    assert ThemeColors.TEXT_PRIMARY.lower() == "#ededee"


def test_fonts_defined() -> None:
    """I font devono essere definiti."""
    assert ThemeFonts.SANS == "Noto Sans"
    assert ThemeFonts.MONO == "Sarasa Mono SC"


def test_shortcuts_unique() -> None:
    """Le scorciatoie principali devono essere distinte."""
    shortcuts: list[str] = [
        Shortcuts.ADD_FEED,
        Shortcuts.REFRESH_ALL,
        Shortcuts.REFRESH_CURRENT,
        Shortcuts.REMOVE_FEED,
        Shortcuts.SEARCH,
        Shortcuts.QUIT,
    ]
    assert len(shortcuts) == len(set(shortcuts))


def test_paths_resolve_to_home() -> None:
    """I percorsi XDG devono puntare sotto la home utente."""
    home_str: str = str(Paths.HOME)
    assert str(Paths.CONFIG_HOME).startswith(home_str) or "XDG" in home_str


def test_ui_constraints_reasonable() -> None:
    """I vincoli UI devono essere ragionevoli."""
    assert UIConstraints.WINDOW_MIN_WIDTH > 0
    assert UIConstraints.WINDOW_MIN_HEIGHT > 0
    assert UIConstraints.MAX_GRID_COLUMNS == 3


def test_feed_defaults_reasonable() -> None:
    """I default dei feed devono essere ragionevoli."""
    assert FeedDefaults.REFRESH_INTERVAL_SECONDS >= 30
    assert FeedDefaults.MAX_ITEMS_PER_FEED > 0
    assert FeedDefaults.MAX_ITEM_AGE_HOURS > 0
    assert "news-aggregator" in FeedDefaults.USER_AGENT.lower() or FeedDefaults.USER_AGENT


def test_typography_hierarchy() -> None:
    """La gerarchia tipografica deve rispettare §3.3."""
    assert ThemeTypography.TITLE_SIZE > ThemeTypography.BODY_SIZE
    assert ThemeTypography.CARD_HEADER_SIZE == 13
    assert ThemeTypography.BUTTON_SIZE == 12
    assert ThemeTypography.BADGE_SIZE == 10


def test_spacing_radius_hierarchy_neumorphism() -> None:
    """La gerarchia di border-radius deve essere 8 < 12 < 16 < 24.

    Le linee guida Neumorphism §06 raccomandano di limitare il
    border-radius a 2-3 valori coerenti (12 / 16 / 24 nell'originale,
    noi aggiungiamo 8 per i badge pill).
    """
    assert ThemeSpacing.BORDER_RADIUS_SM == 8
    assert ThemeSpacing.BORDER_RADIUS == 12
    assert ThemeSpacing.BORDER_RADIUS_LG == 16
    assert ThemeSpacing.BORDER_RADIUS_XL == 24
    assert ThemeSpacing.BORDER_RADIUS_SM < ThemeSpacing.BORDER_RADIUS
    assert ThemeSpacing.BORDER_RADIUS < ThemeSpacing.BORDER_RADIUS_LG
    assert ThemeSpacing.BORDER_RADIUS_LG < ThemeSpacing.BORDER_RADIUS_XL
