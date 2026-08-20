"""Token di colore, font e spaziatura per il tema Neumorphism.

Tutti i componenti UI devono referenziare esclusivamente i token definiti
in questo modulo. È vietato usare valori hex, font o dimensioni hardcoded
altrove nell'applicazione (vincolo §5.1.5).

Il tema è esclusivamente Neumorphism (dark): non esiste un tema chiaro e
non esiste un selettore di tema (vincolo §5.1.9). Lo sfondo è #121213 e
ogni elemento condivide lo stesso "materiale": la profondità nasce da
due ombre contrapposte (chiara in alto a sinistra, scura in basso a
destra), coerenti con un'unica fonte di luce virtuale.
"""

from __future__ import annotations


class ThemeColors:
    """Token di colore semantici per Neumorphism.

    Nessun componente UI può usare valori hex al di fuori di questa classe.
    I token sono organizzati per ruolo semantico, non per valore cromatico.
    """

    # Accento primario — Arancione Neumorphism
    PRIMARY: str = "#ff6600"
    PRIMARY_DARK: str = "#cc5200"
    PRIMARY_SOFT: str = "#ff8c3d"

    # Azioni distruttive / Avviso — Rosso "bad"
    DANGER: str = "#e56a65"
    DANGER_DARK: str = "#b04f4b"

    # Stato positivo — Verde "good"
    GOOD: str = "#55c98f"

    # Colori neutrali e di supporto
    # Nel neumorphism lo sfondo di elementi e contenitore coincide:
    # l'ombra crea la forma, non il colore.
    BG_MAIN: str = "#121213"
    BG_CARD: str = "#121213"
    BG_INPUT: str = "#121213"
    BG_HOVER: str = "#1a1a1c"
    BG_TOOLTIP: str = "#1a1a1c"
    BG_SELECTION: str = "#ff6600"

    # Ombre neumorphic: chiara (alto/sinistra) e scura (basso/destra)
    SHADOW_LIGHT: str = "#1e1e21"
    SHADOW_DARK: str = "#000000"
    SHADOW_DARK_SOFT: str = "#030304"

    # Bordi: nel neumorphism i bordi simulano le ombre, non sono contorni
    BORDER: str = "#1e1e21"          # = SHADOW_LIGHT, per compatibilità
    BORDER_DARK: str = "#000000"     # = SHADOW_DARK, lato opposto
    BORDER_FOCUS: str = "#ff6600"    # anello di accento al focus

    TEXT_PRIMARY: str = "#ededee"
    TEXT_SECONDARY: str = "#97979b"
    TEXT_DISABLED: str = "#616166"
    TEXT_ON_PRIMARY: str = "#121213"  # testo scuro su accento arancione

    # Indicatori di stato (palette neumorphism)
    STATUS_RUNNING: str = "#55c98f"
    STATUS_ERROR: str = "#e56a65"
    STATUS_STOPPED: str = "#616166"
    STATUS_PAUSED: str = "#ff6600"

    # Link
    LINK: str = "#ff6600"
    LINK_VISITED: str = "#ff8c3d"


class ThemeFonts:
    """Famiglie di font per Neumorphism.

    Noto Sans per il testo dell'interfaccia (sans-serif pulita, leggibile
    anche con il basso contrasto tipico del neumorphism), Sarasa Mono SC
    per output tecnico, log e contenuto monospace.
    """

    SANS: str = "Noto Sans"
    MONO: str = "Sarasa Mono SC"
    FALLBACK_SANS: str = "Sans Serif"
    FALLBACK_MONO: str = "Monospace"


class ThemeSpacing:
    """Spaziature standard per layout e componenti Neumorphism.

    Il neumorphism richiede più "respiro" attorno agli elementi rispetto
    a un tema flat, perché le ombre hanno bisogno di spazio per essere
    percepite. I border-radius sono più generosi (12/16/24 px).
    """

    XS: int = 4
    SM: int = 8
    MD: int = 12
    LG: int = 16
    XL: int = 24
    XXL: int = 32

    # Gerarchia di border-radius coerente (linee guida §06)
    BORDER_RADIUS_SM: int = 8
    BORDER_RADIUS: int = 12
    BORDER_RADIUS_LG: int = 16
    BORDER_RADIUS_XL: int = 24

    BORDER_WIDTH: int = 1

    STATUS_INDICATOR_SIZE: int = 8


class ThemeTypography:
    """Gerarchia tipografica con dimensioni leggermente più generose.

    Il neumorphism beneficia di body text un po' più grande per
    compensare il ridotto contrasto visivo causato dalle ombre.
    """

    CARD_HEADER_SIZE: int = 13
    CARD_HEADER_WEIGHT: int = 600
    CARD_HEADER_LETTER_SPACING: float = 0.5

    BUTTON_SIZE: int = 12
    BUTTON_WEIGHT: int = 600

    BODY_SIZE: int = 12
    BODY_WEIGHT: int = 400

    BADGE_SIZE: int = 10
    BADGE_WEIGHT: int = 500

    TITLE_SIZE: int = 16
    TITLE_WEIGHT: int = 700

    SUBTITLE_SIZE: int = 14
    SUBTITLE_WEIGHT: int = 500


class ThemeAnimation:
    """Durate e curve di easing per animazioni neumorphic.

    Transizioni morbide (150-300 ms) con easing OutCubic: quando un
    bottone viene premuto l'ombra si inverte fluidamente, non a scatti.
    """

    DURATION_FAST_MS: int = 150
    DURATION_NORMAL_MS: int = 250
    DURATION_SLOW_MS: int = 300

    EASE_OUT: str = "OutCubic"
    EASE_IN_OUT: str = "InOutCubic"
