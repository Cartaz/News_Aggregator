# News Aggregator

Applicazione **desktop Python** (PySide6) per KDE Plasma / Breeze Dark su
CachyOS (Arch Linux). Aggrega feed RSS/Atom multipli in un'unica dashboard
**solo testo**, senza immagini né pubblicità, risparmiando banda dati.

## Caratteristiche

- **Dashboard multi-feed**: inserisci uno o più URL RSS/Atom e raccogli tutti gli articoli in un'unica vista.
- **Solo testo**: il sommario di ogni articolo è ripulito da HTML, immagini, embed e pubblicità inline.
- **Refresh automatico**: configurabile (5, 15, 30, 60, 120, 360 minuti).
- **Ricerca full-text**: filtra gli articoli per parola chiave (Ctrl+F).
- **Apri nel browser**: il link originale è disponibile come clic, ma il sommario resta in-app.
- **System tray KDE**: icona nel tray con menu contestuale (Mostra / Aggiorna tutti / Esci).
- **Notifiche desktop** per nuovi articoli (opzionale).
- **Stato persistente**: feed e articoli letti/non-letti salvati in JSON (XDG).
- **Tema Breeze Dark nativo**: token di colore centralizzati, font `Noto Sans`, nessun colore hardcoded.
- **Architettura modulare a 3 livelli** (`config/`, `core/`, `ui/`), framework-agnostic nel core.

## Requisiti

- Python 3.12+ (testato su 3.12, 3.13, 3.14)
- PySide6 ≥ 6.10.1 (versioni precedenti non supportano Python 3.14)
- `feedparser`, `requests`
- Font `Noto Sans` (raccomandato `Sarasa Mono SC` per output monospace)
- KDE Plasma 6 con tema Breeze Dark

## Installazione

### Opzione A — Installazione locale (raccomandata per sviluppo)

```bash
cd ~/apps
git clone <repo-url> news-aggregator
cd news-aggregator
./install.sh
```

Lo script:
1. Crea un venv `.venv` nella directory del progetto.
2. Installa le dipendenze da `requirements.txt`.
3. Genera `~/.local/share/applications/news-aggregator.desktop` con percorsi assoluti nel campo `Exec`.
4. Copia l'icona SVG in `~/.local/share/icons/hicolor/scalable/apps/`.
5. Aggiorna la cache desktop e icone.

Dopo l'installazione, lancia l'app dal menu applicazioni KDE (cerca "News Aggregator").

### Opzione B — Pacchetto Arch/CachyOS

```bash
makepkg -si
```

Installa in `/usr/bin/news-aggregator`, `/usr/lib/python*/site-packages/news_aggregator/` e `/usr/share/applications/`.

## Avvio rapido (senza installazione)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Scorciatoie da tastiera

| Scorciatoia        | Azione                         |
|--------------------|--------------------------------|
| `Ctrl+N`           | Aggiungi un nuovo feed URL     |
| `Ctrl+R`           | Aggiorna tutti i feed          |
| `Ctrl+Shift+R`     | Aggiorna il feed corrente      |
| `Ctrl+D`           | Elimina il feed corrente       |
| `Ctrl+F`           | Focus sulla ricerca articoli   |
| `Ctrl+O`           | Apri il link dell'articolo corrente nel browser |
| `Ctrl+Q`           | Esci dall'applicazione         |

## Struttura del progetto

```
news_aggregator/
├── main.py                       # Orchestratore puro
├── requirements.txt
├── install.sh
├── PKGBUILD
├── README.md
├── assets/icons/news-aggregator.svg
├── config/                       # Livello dichiarativo (nessuna dipendenza)
│   ├── constants.py              # AppMeta, Paths, FeedDefaults, Shortcuts
│   ├── theme.py                  # ThemeColors, ThemeFonts, ThemeSpacing
│   └── settings.py               # SettingsManager (JSON XDG)
├── core/                         # Logica di business, framework-agnostic
│   ├── exceptions.py
│   ├── models.py                 # FeedSource, FeedItem (dataclass)
│   ├── event_bus.py              # Singleton pub/sub, NO Qt
│   ├── feed_parser.py            # RSS/Atom → FeedItem
│   ├── feed_fetcher.py           # HTTP + parse
│   ├── feed_serializer.py        # JSON I/O
│   ├── feed_manager.py           # Add/remove/refresh
│   └── app_controller.py         # Facade UI
├── ui/                           # PySide6, dipende da core e config
│   ├── event_bridge.py           # Thread-safe Qt bus bridge
│   ├── main_window.py            # QMainWindow
│   ├── main_window_actions.py    # Azioni utente (split per limite 300 righe)
│   ├── main_window_handlers.py   # Handler EventBus (split per limite 300 righe)
│   ├── tray_icon.py              # QSystemTrayIcon
│   ├── styles/breeze_dark.py     # QSS globale da ThemeColors
│   └── widgets/                  # ActionButton, Card, FeedInput, NewsView, ...
└── tests/                        # pytest + pytest-qt
```

## Test

```bash
.venv/bin/pip install pytest pytest-qt
.venv/bin/python -m pytest tests/ -v
```

Per escludere i test UI (richiedono display X):

```bash
.venv/bin/python -m pytest tests/ -v -m "not ui"
```

## File utente (XDG)

| Percorso                                     | Contenuto                          |
|----------------------------------------------|------------------------------------|
| `~/.config/news-aggregator/settings.json`    | Impostazioni utente                |
| `~/.local/share/news-aggregator/feeds.json`  | Catalogo feed e articoli           |
| `~/.local/state/news-aggregator/app.log`     | Log rotante (5 MB × 3)             |

## Architettura

L'applicazione segue un'architettura a 3 livelli con regole di dipendenza
strette (vedi `System_Prompt_Software_Engineer.md`):

```
┌─────────┐      ┌─────────┐
│   ui/   │ ───► │  core/  │
└────┬────┘      └────┬────┘
     │    ┌───────┐   │
     └──► │config/│ ◄─┘
          └───────┘
```

- `ui/` → `core/` e `config/` (OK)
- `core/` → `config/` (OK)
- `core/` → `ui/` (VIETATO)
- `config/` → nessuno (puramente dichiarativo)

La comunicazione cross-livello avviene tramite **EventBus** singleton
(`core/event_bus.py`), che è framework-agnostic. Per aggiornamenti GUI
thread-safe dal worker thread, il bridge `ui/event_bridge.py` usa
`QTimer.singleShot(0, callback)` per marshallare la chiamata sul thread
Qt principale.

## Licenza

GPL-3.0-or-later
