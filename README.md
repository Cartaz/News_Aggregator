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
- refresh singolo, globale e automatico in background;
- progresso reale del refresh globale;
- cancellazione dei refresh durante lo shutdown;
- apertura degli articoli nel browser di sistema;
- favicon delle sorgenti risolte in background, memorizzate in cache e rese monocromatiche arancioni dalla UI;
- system tray e notifiche opzionali;
- viewer del log applicativo;
- scala tipografica regolabile e responsive;
- scorciatoie da tastiera e navigazione con frecce nella lista articoli.

## Interfaccia Qt Quick

La UI vive in `ui/qml/` e usa un unico design system Dark Neumorphism:

- superficie `rgb(20,20,20)` / `#141414`;
- accento `rgb(255,102,0)` / `#ff6600`;
- testo `#e1e1e1`, `#878787`, `#5a5a5a`;
- font UI canonico **Cantarell**;
- raggi 28 / 22 / 16 / 12 px;
- pannelli principali raised, righe soft-raised, campi/pressioni/selezioni inset;
- selezione = profondità inset + testo/bordo arancione con glow leggero e semitrasparente;
- scala tipografica responsive rispetto alla finestra, moltiplicata per la preferenza utente;
- controlli custom con focus da tastiera e metadati `Accessible`.

L'icona applicativa viene riutilizzata nell'header e nella voce `Tutti gli articoli`. Le sorgenti singole usano la favicon del relativo sito quando disponibile; l'immagine originale viene conservata nella cache locale, mentre `AccentIcon.qml` applica la colorizzazione arancione tramite `MultiEffect`, evitando una palette multicolore nella sidebar. Le categorie mantengono il proprio simbolo neutro.

`RaisedSurface.qml` usa `RectangularShadow`. `InsetSurface.qml` nasconde uno shader SDF riutilizzabile; `install.sh` lo precompila con `pyside6-qsb --qt6`. Il `.qsb` generato è un artefatto locale e non viene versionato.

Le collezioni dinamiche usano `ListView`; gli articoli e le sorgenti sono esposti da Python tramite `QAbstractListModel` con ruoli stabili. I delegate vengono riutilizzati e non possiedono stato operativo persistente. Gli aggiornamenti non strutturali del model sorgenti usano notifiche `dataChanged` mirate invece di reset completi, così la sidebar non ricrea inutilmente tutti i delegate durante navigazione e refresh.

## Architettura e concorrenza

`main.py` è il composition root: crea `QApplication`, un solo `AppController`, `UiController`, la shell QML e il tray, e garantisce cleanup deterministico nel `finally`.

`core/` resta indipendente da Qt. `FeedManager` possiede catalogo e persistenza; `AppController` possiede lo stato operativo e coordina refresh, impostazioni ed eventi. `SiteIconService` nasconde discovery HTTP, limiti di download, cache positiva/negativa e worker delle favicon; non espone rete a QML. `ui/controller.py` coordina soltanto lo stato di vista e i modelli della schermata principale; `ui/preferences.py` e `ui/diagnostics.py` espongono interfacce QML focalizzate per preferenze e log. Gli adapter traducono comandi Qt in chiamate del controller e inoltrano eventi tramite signal Qt queued senza possedere regole di dominio o persistenza.

Le mutazioni persistenti avviate dalla UI vengono serializzate dal `MutationWorker` del controller, quindi le scritture JSON non bloccano il thread GUI. Anche il recupero delle favicon resta fuori dal thread GUI e ha concorrenza limitata. Python resta la sorgente canonica; QML mantiene soltanto stato di presentazione temporaneo come focus, modal aperto e ricerca corrente.

Su Linux l'avvio applica automaticamente un limite conservativo agli arena glibc (`MALLOC_ARENA_MAX=2`) prima degli import pesanti, rispettando un eventuale valore impostato esplicitamente dall'utente. Al termine dei refresh e quando l'app entra nel tray viene richiesto il rilascio delle pagine native inutilizzate; nel tray la finestra Qt Quick rilascia inoltre risorse grafiche e scene graph ricreabili. Queste ottimizzazioni sono best-effort e diventano no-op sulle piattaforme dove le primitive native non sono disponibili.

Non vengono usati WebEngine, QWebChannel, HTML, CSS o JavaScript di frontend.

## Requisiti

- Linux desktop; CachyOS/Arch + KDE è la piattaforma primaria;
- Python 3.12 o superiore;
- accesso a Internet durante l'installazione delle dipendenze e per aggiornare feed/favicon;
- stack grafico Qt/OpenGL funzionante;
- privilegi amministrativi disponibili solo se `install.sh` deve installare Cantarell tramite il package manager di sistema.

## Installazione

Dalla root del progetto:

```bash
chmod +x install.sh
./install.sh
```

Lo script:

1. verifica Python 3.12+;
2. verifica il font Cantarell e, se manca, lo installa automaticamente sui sistemi supportati (`cantarell-fonts` su Arch/CachyOS, `fonts-cantarell` su Debian/Ubuntu, `abattis-cantarell-vf-fonts` su Fedora);
3. crea, riusa o ripara `.venv`;
4. installa le dipendenze runtime;
5. individua il `qsb` abbinato a PySide6 (con fallback ai percorsi Qt di sistema);
6. compila `ui/qml/shaders/neumorphic_inset.frag` in un pacchetto multi-backend `.qsb` tramite `--qt6`;
7. verifica che il pacchetto contenga una variante GLSL e che i moduli Qt Quick critici siano importabili.

Su Arch/CachyOS, se il tool QSB non fosse disponibile dal virtualenv, il pacchetto di sistema è `qt6-shadertools`.

## Avvio

```bash
.venv/bin/python main.py
```

Non serve attivare la virtualenv con `source` e non serve prefissare manualmente `MALLOC_ARENA_MAX=2`: su Linux la policy viene applicata automaticamente dall'entry point.

## Test

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m compileall -q main.py config core ui tests
.venv/bin/python -m pytest
```

La CI separa i test core/contratti dagli E2E Qt Quick reali, eseguiti sotto Xvfb con rendering software OpenGL.

## Struttura

```text
news_aggregator/
├── main.py
├── install.sh
├── requirements.txt
├── requirements-dev.txt
├── config/
├── core/
│   ├── app_controller.py
│   ├── feed_discovery.py
│   ├── feed_fetcher.py
│   ├── feed_manager.py
│   ├── mutation_worker.py
│   ├── native_memory.py
│   ├── refresh_state.py
│   └── site_icon_service.py
├── ui/
│   ├── controller.py
│   ├── models.py
│   ├── preferences.py
│   ├── diagnostics.py
│   ├── native_actions.py
│   ├── tray.py
│   ├── window.py
│   └── qml/
│       ├── Main.qml
│       ├── AppDialogs.qml
│       ├── Theme.qml
│       ├── AccentIcon.qml
│       ├── RaisedSurface.qml
│       ├── InsetSurface.qml
│       ├── NeuButton.qml
│       ├── NeuToggle.qml
│       ├── SourceRow.qml
│       ├── ArticleRow.qml
│       └── shaders/
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
