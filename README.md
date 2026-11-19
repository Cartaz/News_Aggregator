# News Aggregator

News Aggregator è un'applicazione desktop Python per aggregare feed RSS/Atom in una vista testuale, senza immagini o pubblicità inline. Il backend resta Python; la presentazione usa **PySide6 + Qt Quick/QML** e non incorpora un browser Chromium/WebEngine.

## Funzioni principali

- sorgenti RSS/Atom singole e categorie;
- vista aggregata di tutti i feed;
- ricerca locale negli articoli;
- filtro `Solo non letti` persistente;
- stato letto/non letto persistente;
- con `Segna come letto al cambio articolo` attivo, l'articolo corrente resta non letto mentre viene visualizzato e passa a letto quando si seleziona la notizia successiva;
- aggiunta, rinomina, categorizzazione e rimozione dei feed;
- refresh singolo, globale e automatico in background: il primo parte subito all'avvio, poi ogni 15 minuti (configurabile da 1 minuto a 6 ore);
- gli errori dei singoli feed restano visibili nella sidebar senza notifiche ripetute; i refresh avviati a mano riportano l'esito;
- progresso reale del refresh globale;
- cancellazione dei refresh durante lo shutdown;
- apertura degli articoli nel browser di sistema;
- favicon delle sorgenti risolte in background, memorizzate in cache e rese monocromatiche arancioni dalla UI;
- system tray e notifiche opzionali;
- viewer del log applicativo;
- versione installata visibile nel dialogo Impostazioni;
- scala tipografica regolabile e responsive;
- scorciatoie da tastiera e navigazione con frecce nella lista articoli.

## Interfaccia Qt Quick

La UI vive in `ui/qml/` e usa un unico design system Dark Neumorphism:

- superficie `rgb(20,20,20)` / `#141414`;
- accento `rgb(255,102,0)` / `#ff6600`;
- testo `#e1e1e1`, `#878787`, `#5a5a5a`;
- font UI canonico **Noto Sans**;
- raggi 28 / 22 / 16 / 12 px;
- pannelli principali raised, righe soft-raised, campi/pressioni/selezioni inset;
- selezione = profondità inset + testo/bordo arancione con glow leggero e semitrasparente;
- scala tipografica responsive rispetto alla finestra, moltiplicata per la preferenza utente;
- controlli custom con focus da tastiera e metadati `Accessible`.

L'icona applicativa viene riutilizzata nell'header e nella voce `Tutti gli articoli`. Le sorgenti singole usano la favicon del relativo sito quando disponibile; l'immagine originale viene conservata nella cache locale, mentre `AccentIcon.qml` applica la colorizzazione arancione tramite `MultiEffect`, evitando una palette multicolore nella sidebar. Le categorie mantengono il proprio simbolo neutro.

`RaisedSurface.qml` usa `RectangularShadow`. `InsetSurface.qml` nasconde uno shader SDF riutilizzabile; `install.sh` lo precompila con `pyside6-qsb --qt6`. Il `.qsb` generato è un artefatto locale e non viene versionato.

Le collezioni dinamiche usano `ListView`; gli articoli e le sorgenti sono esposti da Python tramite `QAbstractListModel` con ruoli stabili. I delegate vengono riutilizzati e non possiedono stato operativo persistente. I model evitano i reset completi quando non servono: cambi di stato (letto, contatori, icone) diventano notifiche `dataChanged` mirate e i nuovi articoli arrivati con un refresh vengono inseriti in cima, così la lista conserva scroll e delegate. Il reset resta solo per cambi di vista o filtro.

## Architettura e concorrenza

`main.py` è il composition root: crea `QApplication`, un solo `AppController`, `UiController`, la shell QML e il tray, e garantisce cleanup deterministico nel `finally`.

`core/` resta indipendente da Qt. `FeedManager` possiede catalogo e persistenza; `AppController` possiede lo stato operativo e coordina refresh, impostazioni ed eventi. `SiteIconService` nasconde discovery HTTP, limiti di download, cache positiva/negativa e worker delle favicon; non espone rete a QML. `ui/controller.py` coordina soltanto lo stato di vista e i modelli della schermata principale; `ui/preferences.py` e `ui/diagnostics.py` espongono interfacce QML focalizzate per preferenze e log. Gli adapter traducono comandi Qt in chiamate del controller e inoltrano eventi tramite signal Qt queued senza possedere regole di dominio o persistenza.

Le mutazioni avviate dalla UI vengono serializzate dal `MutationWorker` del controller, quindi nessuna scrittura blocca il thread GUI. Anche il recupero delle favicon resta fuori dal thread GUI e ha concorrenza limitata. Python resta la sorgente canonica; QML mantiene soltanto stato di presentazione temporaneo come focus, modal aperto e ricerca corrente.

La persistenza di `feeds.json` ha due velocità. Aggiunta, rimozione e modifica di un feed sono transazionali: il file viene scritto prima che la modifica diventi visibile e un errore del disco arriva all'utente. Risultati dei refresh e stato letto vengono applicati in memoria e scritti in un'unica volta: dopo pochi secondi, alla fine di un refresh globale e sempre alla chiusura. Un refresh che riceve solo `304 Not Modified` non riscrive il file.

Rete: `requests` è il trasporto principale; `curl_cffi` (impronta TLS di un browser) interviene solo quando la risposta indica un blocco anti-bot (403/503, challenge Cloudflare, errore TLS). Le risposte sono limitate a 10 MB per i feed e a 1 MB per le icone. Con la rete assente un refresh fallisce subito, senza tentare la discovery. La discovery prova al massimo 5 link dichiarati e 5 link `<a>` dello stesso sito, solo http(s). Gli articoli privi di data mantengono la data in cui sono stati visti la prima volta.

Quando l'app entra nel tray, la finestra Qt Quick rilascia risorse grafiche e scene graph ricreabili. `Ctrl+C` e `SIGTERM` chiudono l'app passando dallo shutdown normale.

Non vengono usati WebEngine, QWebChannel, HTML, CSS o JavaScript di frontend.

## Requisiti

- Linux desktop; CachyOS/Arch + KDE è la piattaforma primaria;
- Python 3.12 o superiore;
- accesso a Internet durante l'installazione delle dipendenze e per aggiornare feed/favicon;
- stack grafico Qt/OpenGL funzionante;
- privilegi amministrativi disponibili solo se `install.sh` deve installare Noto Sans tramite il package manager di sistema.

## Installazione

Dalla root del progetto:

```bash
chmod +x install.sh
./install.sh
```

Lo script:

1. verifica Python 3.12+;
2. verifica il font Noto Sans e, se manca, lo installa automaticamente sui sistemi supportati (`noto-fonts` su Arch/CachyOS, `fonts-noto-core` su Debian/Ubuntu, `google-noto-sans-fonts` su Fedora);
3. crea, riusa o ripara `.venv`;
4. installa le dipendenze runtime;
5. usa esclusivamente `pyside6-qsb` della stessa `.venv` di PySide6;
6. compila `ui/qml/shaders/neumorphic_inset.frag` in un pacchetto multi-backend `.qsb` tramite `--qt6`;
7. verifica che il pacchetto contenga una variante GLSL e che i moduli Qt Quick critici siano importabili;
8. carica `Main.qml` offscreen con percorsi XDG temporanei, senza modificare i dati utente.

Se `pyside6-qsb` manca, reinstalla PySide6 nella `.venv`: un compilatore Qt di sistema potrebbe produrre un pacchetto incompatibile con il runtime. Su Debian/Ubuntu il plugin desktop X11 richiede anche `libxcb-cursor0` e le librerie Qt/OpenGL indicate nella CI.

## Avvio

```bash
.venv/bin/python main.py
```

Non serve attivare la virtualenv con `source`. Il livello di log si regola con `NEWS_AGGREGATOR_LOG_LEVEL` (per esempio `DEBUG`).

## Test

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m compileall -q main.py config core ui tests
.venv/bin/python -m pytest
```

I test verificano comportamenti, non il testo del sorgente. L'integrazione HTTP usa un server locale reale per discovery, cache condizionale e persistenza; le risposte di rete simulate passano da `tests/http_fakes.py`. Le prove UI coprono focus, filtri, aggiornamenti esterni, log asincrono, chiusura e l'assenza di reset inutili dei model. `tests/test_architecture.py` controlla con l'AST che `core/` e `config/` non dipendano da Qt né dalla UI, e che ogni testo QML sia `PlainText`: i contenuti dei feed non sono mai interpretati come markup.

La CI esegue i test core su Python 3.12 e 3.14 e gli E2E Qt Quick reali sotto Xvfb con rendering software OpenGL. In locale gli E2E girano anche con `QT_QPA_PLATFORM=offscreen`.

Il rapporto dell'audit del 29 settembre 2026 è in [docs/audit-2026-09-29.md](docs/audit-2026-09-29.md).

## Struttura

```text
News_Aggregator/
├── main.py                  # composition root, logging, segnali, ciclo di vita
├── install.sh               # venv, dipendenze, shader, smoke test QML
├── requirements.txt / requirements-dev.txt
├── config/
│   ├── constants.py         # metadati, percorsi XDG, default dei feed, limiti UI
│   ├── exceptions.py        # AppError e errori di configurazione
│   └── settings.py          # impostazioni validate e persistite
├── core/                    # dominio, rete e persistenza; nessuna dipendenza da Qt
│   ├── app_controller.py    # stato operativo, refresh, eventi, comandi asincroni
│   ├── diagnostics.py       # coda del log applicativo
│   ├── exceptions.py
│   ├── feed_discovery.py    # percorsi candidati e override per sito
│   ├── feed_fetcher.py      # fetch, auto-discovery, parsing
│   ├── feed_http.py         # trasporto HTTP, limiti, fallback anti-WAF
│   ├── feed_link_extractor.py
│   ├── feed_manager.py      # catalogo, refresh, persistenza a due velocità
│   ├── feed_parser.py       # RSS/Atom -> FeedItem in solo testo
│   ├── feed_serializer.py
│   ├── item_identity.py     # identità stabile degli articoli
│   ├── models.py
│   ├── mutation_worker.py
│   ├── refresh_state.py
│   └── site_icon_service.py
├── ui/
│   ├── controller.py        # adapter QML per la schermata principale
│   ├── models.py            # QAbstractListModel di sorgenti e articoli
│   ├── preferences.py
│   ├── diagnostics.py
│   ├── native_actions.py    # apertura link nel browser di sistema
│   ├── tray.py
│   ├── window.py
│   └── qml/                 # Main, AppDialogs, Theme, componenti Neu*, Toast, shader
└── tests/
```

## File utente

| Percorso | Contenuto |
|---|---|
| `~/.config/news-aggregator/settings.json` | impostazioni |
| `~/.local/share/news-aggregator/feeds.json` | feed, articoli e stato letto |
| `~/.local/share/news-aggregator/site-icons/` | cache favicon delle sorgenti |
| `~/.local/state/news-aggregator/app.log` | log rotante |

La migrazione da WebEngine non cambia i percorsi esistenti. La chiave sperimentale `font_family`, se presente in un vecchio `settings.json`, viene ignorata come impostazione obsoleta senza perdere le altre preferenze.

## Licenza

GPL-3.0-or-later.
