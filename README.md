# News Aggregator

Applicazione desktop Python per aggregare feed RSS/Atom in una vista testuale, senza immagini o pubblicità inline. Il backend resta Python; l'interfaccia è HTML5/CSS3/JavaScript renderizzata all'interno dell'app tramite Qt WebEngine.

## Funzioni

- aggiunta di URL RSS/Atom o homepage con auto-discovery del feed;
- sorgenti singole, categorie e mega-feed globale;
- articoli ordinati per data con finestra temporale gestita dal core;
- ricerca full-text locale nella vista corrente;
- filtro solo non letti e stato letto/non letto persistente;
- rinomina delle sorgenti e assegnazione a categorie;
- refresh singolo e globale in background con avanzamento reale;
- refresh automatico configurabile;
- apertura degli articoli nel browser di sistema;
- system tray, conteggio non letti, notifiche opzionali e close-to-tray;
- viewer del log reale dell'applicazione;
- persistenza XDG di feed, impostazioni e log.

## Interfaccia

La UI segue un unico design system **Dark Neumorphism monocromatico con accent arancione**:

- superficie unica: `#141414` per background, pannelli, card e controlli;
- accent unico: `#FF6600` per selezione, focus, indicatori e glow;
- profondità tramite ombre esterne e `inset`, non tramite superfici più chiare;
- nessun framework visuale, nessun gradiente sulle superfici;
- HTML semantico, focus da tastiera, focus trap nei modali, `prefers-reduced-motion` e layout responsive.

I file del frontend sono in `ui/web/` e non contengono business logic. La comunicazione con Python usa `QWebChannel`; non viene avviato alcun server HTTP locale.

## Architettura

```text
Python core / filesystem / rete / thread
                ↓
         AppController + EventBus
                ↓
          ui/bridge.py (QWebChannel)
                ↓
       HTML + CSS + JavaScript
                ↓
             utente
```

Struttura principale:

```text
news_aggregator/
├── main.py
├── config/
│   ├── constants.py
│   ├── settings.py
│   └── theme.py
├── core/
│   ├── app_controller.py
│   ├── event_bus.py
│   ├── feed_fetcher.py
│   ├── feed_manager.py
│   └── ...
├── ui/
│   ├── bridge.py
│   ├── tray.py
│   ├── window.py
│   └── web/
│       ├── index.html
│       ├── styles.css
│       ├── log-viewer.css
│       ├── state.js
│       ├── articles.js
│       ├── dialogs.js
│       └── app.js
└── tests/
```

`core/` non importa Qt e rimane framework-agnostic. `ui/bridge.py` serializza soltanto dati e comandi necessari alla presentazione; le operazioni di rete e persistenza rimangono nel backend.

## Requisiti

- Python 3.12+
- PySide6 >= 6.10.1
- feedparser >= 6.0.10
- requests >= 2.31.0
- curl_cffi >= 0.7.0
- Brotli >= 1.0.9

Qt WebEngine e Qt WebChannel sono forniti dalla dipendenza PySide6 già usata dall'applicazione; non è richiesto un framework frontend aggiuntivo.

## Installazione locale

```bash
git clone <repo-url> news-aggregator
cd news-aggregator
./install.sh
```

Lo script crea `.venv`, installa le dipendenze e registra l'applicazione nel menu desktop.

## Avvio rapido

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Scorciatoie

| Scorciatoia | Azione |
|---|---|
| `Ctrl+N` | Aggiungi feed |
| `Ctrl+R` | Aggiorna tutti |
| `Ctrl+Shift+R` | Aggiorna feed selezionato |
| `Ctrl+D` | Rimuovi feed selezionato |
| `Ctrl+F` | Cerca articoli |
| `Ctrl+M` | Segna articolo come letto |
| `Ctrl+O` | Apri articolo nel browser |
| `Ctrl+H` | Nascondi nel tray |
| `Ctrl+Q` | Esci |

## Test

```bash
.venv/bin/python -m pytest tests/ -v
```

I test UI includono verifiche statiche sul contratto visivo (`#141414`, `#FF6600`, assenza di gradienti e colori superficie vietati), HTML semantico e bridge.

## File utente

| Percorso | Contenuto |
|---|---|
| `~/.config/news-aggregator/settings.json` | impostazioni |
| `~/.local/share/news-aggregator/feeds.json` | feed, articoli e stato letto |
| `~/.local/state/news-aggregator/app.log` | log rotante |

## Licenza

GPL-3.0-or-later
