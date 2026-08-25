# News Aggregator

News Aggregator è un'applicazione desktop Python per aggregare feed RSS/Atom in una vista testuale, senza immagini o pubblicità inline. Il backend resta Python; l'interfaccia è HTML5/CSS3/JavaScript renderizzata dentro Qt WebEngine e collegata al core tramite QWebChannel.

## Funzioni principali

- sorgenti RSS/Atom singole e categorie;
- vista aggregata di tutti i feed;
- ricerca locale negli articoli;
- filtro `Solo non letti`;
- stato letto/non letto persistente;
- con `Segna come letto al cambio articolo` attivo, l'articolo corrente resta non letto mentre viene visualizzato e passa a letto quando si seleziona la notizia successiva;
- aggiunta, rinomina, categorizzazione e rimozione dei feed;
- refresh singolo, globale e automatico in background;
- progresso reale del refresh globale;
- apertura degli articoli nel browser di sistema;
- system tray e notifiche opzionali;
- viewer del log applicativo.

## Interfaccia

La UI usa un unico design system Dark Neumorphism:

- superficie unica: `#141414`;
- accent unico: `#FF6600`;
- profondità tramite ombre esterne e inset;
- nessun gradiente sulle superfici;
- HTML semantico, focus da tastiera e supporto a `prefers-reduced-motion`.

Il frontend vive in `ui/web/`. Non viene avviato alcun server HTTP locale. Lo stato operativo resta canonico in Python: gli aggiornamenti ordinari arrivano alla UI tramite signal Qt/QWebChannel; quando la finestra torna visibile viene richiesto un resync esplicito, senza polling periodico del backend.

## Requisiti

- Linux desktop;
- Python 3.12 o superiore;
- accesso a Internet durante l'installazione delle dipendenze.

## Installazione

Dalla root del progetto:

```bash
chmod +x install.sh
./install.sh
```

Lo script:

1. verifica che Python sia almeno alla versione 3.12;
2. crea `.venv` se non esiste, riutilizza una virtualenv compatibile oppure la ricrea se è incompleta o usa Python precedente alla 3.12;
3. aggiorna `pip`, `setuptools` e `wheel` dentro il virtual environment;
4. installa le sole dipendenze runtime da `requirements.txt`;
5. verifica che PySide6 WebEngine/WebChannel e le dipendenze di rete siano importabili.

Lo script è ripetibile e può essere rieseguito per aggiornare le dipendenze o riparare una `.venv` non compatibile.

## Avvio

Dopo l'installazione:

```bash
.venv/bin/python main.py
```

Non è necessario attivare il virtual environment con `source`.

## Dipendenze di sviluppo e test

Le dipendenze per i test sono separate da quelle runtime:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -v
```

## Struttura

```text
news_aggregator/
├── main.py
├── install.sh
├── requirements.txt
├── requirements-dev.txt
├── config/
├── core/
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

`core/` resta framework-agnostic. `FeedManager` possiede catalogo e persistenza dei feed; `AppController` possiede lo stato operativo e coordina gli eventi applicativi. La UI comunica con il backend esclusivamente attraverso `ui/bridge.py` e QWebChannel.

## File utente

| Percorso | Contenuto |
|---|---|
| `~/.config/news-aggregator/settings.json` | impostazioni |
| `~/.local/share/news-aggregator/feeds.json` | feed, articoli e stato letto |
| `~/.local/state/news-aggregator/app.log` | log rotante |

## Licenza

GPL-3.0-or-later.
