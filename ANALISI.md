# Analisi del progetto News Aggregator

Data: 19 novembre 2026. Analizzato il commit `62d9aad` (`main`, v1.1.0 più le correzioni dell'audit).

Legenda della verifica, riportata su ogni punto:

- **[ESEGUITO]**: riprodotto eseguendo l'app, i test o uno script di prova.
- **[CODICE]**: confermato leggendo il codice; il comportamento segue direttamente da ciò che c'è scritto.
- **[SOSPETTO]**: ipotesi plausibile, non verificata.

Tutte le esecuzioni sono avvenute su un clone del repository nello scratchpad, con `HOME` e percorsi XDG temporanei. Il progetto e i dati utente reali non sono stati toccati. L'unico file creato nel progetto è questo.

---

## Riassunto

1. È un lettore RSS/Atom desktop (PySide6 + Qt Quick/QML, backend Python) che **si installa, si avvia e supera tutti i 241 test**. La CI su GitHub è verde e nella cronologia git non ci sono segreti.
2. L'architettura (core senza Qt, adapter QML, worker per le scritture, scritture atomiche) è sensata. Non va riscritto.
3. Ci sono però **bug funzionali reali**: nessun aggiornamento all'avvio, articoli senza data che restano sempre "nuovi" in cima, un toast di errore ogni minuto per ogni feed rotto. C'è anche **I/O sproporzionato**: tutto `feeds.json` viene riscritto una volta per feed a ogni ciclo, anche quando il server risponde 304.
4. Strati di compatibilità e codice morto lasciati dai vari passaggi (API "compatibili" mai chiamate, metodi duplicati, costanti inutilizzate, docstring dell'era WebEngine). Circa un quarto dei test controlla solo la presenza di stringhe nel sorgente, non il comportamento.
5. Verdetto: **tenerlo e sistemarlo** in fasi. Le prime tre fasi sono a basso rischio e risolvono quasi tutto ciò che si vede. Solo la persistenza e la sincronizzazione della UI meritano una riscrittura locale.

---

## 1. Cosa fa il progetto, stack e struttura

| Aspetto | Dettaglio |
|---|---|
| Scopo | Aggregatore RSS/Atom "solo testo": sorgenti, categorie, vista aggregata, ricerca, letto/non letto, tray, notifiche |
| Linguaggio | Python ≥ 3.12 (verificato anche con 3.14.10) |
| UI | PySide6 6.12 / Qt Quick, QML in `ui/qml/`, shader SDF compilato con `pyside6-qsb` |
| Rete | `requests`, con fallback `curl_cffi` (impersonificazione di Chrome) per i siti dietro WAF; `feedparser` per il parsing |
| Persistenza | JSON in percorsi XDG: `settings.json`, `feeds.json`, cache delle favicon, log rotante |
| Struttura | `main.py` (composition root) · `config/` (costanti, impostazioni) · `core/` (dominio, rete, persistenza; senza Qt) · `ui/` (adapter QObject, modelli, finestra, tray, QML) · `tests/` (241 test) |
| Avvio | `./install.sh` (crea `.venv`, compila lo shader, fa lo smoke test del QML), poi `.venv/bin/python main.py` |

### Cosa funziona e cosa no (verificato)

| Passo | Esito | Note |
|---|---|---|
| `./install.sh` | ✅ OK | Venv creata, dipendenze installate, shader compilato, `Main.qml` caricato offscreen |
| `compileall` | ✅ OK | |
| `pytest` core e contratti | ✅ 229 passati in 1,3 s | |
| `pytest` E2E QML | ✅ 12 passati in 0,7 s | Eseguiti con `offscreen` (la CI usa Xvfb/xcb) |
| `pyside6-qmllint` | ✅ exit 0 | Un warning sul singleton `Theme` e 238 diagnostiche informative attese |
| `pip check` | ✅ OK | |
| `pip-audit` | ⚠️ | Runtime pulito. `pytest 8.4.2` ha PYSEC-2026-1845, ma il vincolo `<9.0.0` impedisce di installare la versione corretta (9.0.3) |
| Avvio reale di `main.py` (offscreen, 3 feed di prova) | ⚠️ funziona, con difetti | Primo aggiornamento solo dopo 60 s; un feed rotto genera un traceback completo nel log ogni minuto; `Ctrl+C`/SIGINT non chiude l'app (ho dovuto usare SIGTERM) |

---

## 2. Problemi trovati

Ordinati per gravità. "Correzione" indica la soluzione proposta; nessuna è stata applicata.

### Gravità alta

**A1. `feeds.json` riscritto per intero una volta per feed a ogni ciclo, anche con HTTP 304**: [ESEGUITO]
- `core/feed_manager.py:321-332`: `_commit_refresh_result` chiama `_persist_catalog` anche quando `result.not_modified` è vero e non è cambiato nessun articolo.
- Con 20 feed tutti in 304, un solo `refresh_all` ha prodotto **20 riscritture complete** del file. Con 20 feed × 50 articoli il file pesa circa 740 KiB. Con l'intervallo predefinito di 1 minuto sono **circa 20 GiB/giorno** di scritture se l'app resta aperta nel tray (stima calcolata, non misurata sul disco).
- Lo stesso vale per ogni "segna come letto" (`:502-521`): basta navigare tra gli articoli per riscrivere tutto il file. Ogni mutazione copia inoltre l'intero catalogo in memoria (`_snapshot_catalog_locked`).
- **Correzione:** sul 304 aggiornare solo i metadati in memoria, senza persistere. Raggruppare le scritture di un `refresh_all` in un'unica scrittura finale, oppure usare uno scrittore con debounce di qualche secondo. A medio termine valutare SQLite (fase 6).

**A2. Nessun aggiornamento all'avvio; intervallo predefinito di 1 minuto**: [ESEGUITO]
- `core/app_controller.py:440-450` pianifica solo un `threading.Timer(interval)`. Nel log reale l'app parte alle 06:42:46 e fa il primo fetch alle 06:43:46. Con l'intervallo di 6 h l'utente vede dati vecchi per 6 ore, salvo aggiornamento manuale.
- `config/settings.py:26`: il default `refresh_interval_minutes = 1` è aggressivo verso i server remoti e aggrava A1 e A3.
- **Correzione:** lanciare `refresh_all_async()` subito dopo l'avvio (o dopo qualche secondo) e portare il default a 15–30 minuti.

**A3. Articoli senza data: diventano "adesso" a ogni aggiornamento e non scadono mai**: [ESEGUITO]
- `core/feed_parser.py:57` usa `datetime.now()` come data di ripiego. `core/models.py:135` (`replace(item, read=old.read)`) mantiene il `published` **nuovo** invece di quello già salvato.
- Prova: stesso articolo senza data, due aggiornamenti a 1 s di distanza. La data passa da `05:42:03` a `05:42:04`. L'articolo resta quindi sempre in cima e non esce mai dalla finestra di 48 ore.
- **Correzione:** in `replace_items`, se l'articolo esiste già, conservare `old.published` quando il feed non fornisce una data.

### Gravità media

**M1. Un toast di errore ogni minuto per ogni feed rotto**: [CODICE]
- `ui/controller.py:688-702`: ogni evento `feed_refresh_failed` emette un toast, anche durante l'aggiornamento automatico. Con un feed non raggiungibile e il default di 1 minuto, arriva un popup al minuto.
- **Correzione:** mostrare il toast solo per gli aggiornamenti avviati dall'utente o quando lo stato passa da ok a errore. Per il resto basta l'errore nella sidebar, che esiste già (`selectedSourceStatus`).

**M2. Moltiplicazione delle richieste nella discovery, senza limiti**: [ESEGUITO]
- `core/feed_fetcher.py:103-235` con `core/feed_http.py:120-239`: ogni errore di `requests` (anche 404, 500 o DNS) viene ritentato con `curl_cffi`. Una sorgente di tipo homepage offline produce **16 tentativi HTTP sequenziali**, fino a circa 4 minuti con il timeout di 15 s.
- `core/feed_link_extractor.py:116-127`: il ripiego sui tag `<a>` prova **ogni** link che contiene "feed", "rss" o "atom", anche verso altri domini. Una pagina con 60 link di questo tipo ha prodotto **68 richieste** in un solo aggiornamento.
- `core/feed_manager.py:281-289`: un errore di rete temporaneo sull'URL risolto in cache azzera `resolved_feed_url` ed ETag e rilancia tutta la discovery.
- **Correzione:** usare il fallback `curl_cffi` solo su 403 o challenge, limitare i candidati da `<a>` (per esempio 5, stesso dominio) e azzerare la cache solo su 404/410 o su un errore di parsing, non sugli errori di rete.

**M3. Download dei feed senza limite di dimensione**: [CODICE]
- `core/feed_http.py:146-170` usa `requests.get(...).content` senza `stream` né limite, e lo stesso vale per il ramo `curl_cffi`. Un feed malevolo o rotto può far caricare in RAM centinaia di MB. Il servizio favicon ha invece un limite (`_read_response`, `core/site_icon_service.py:119`): le due strade sono incoerenti.
- **Correzione:** riusare un `_read_response` con limite (per esempio 10 MB) anche per i feed.

**M4. UI: `sync()` completo e reset del modello degli articoli per ogni evento**: [ESEGUITO] il conteggio dei reset; [SOSPETTO] l'effetto visivo
- `ui/controller.py` chiama `sync()` in 8 punti (`:585, 592, 611, 641, 649, 657, 669`, oltre al costruttore). Ogni `sync()` copia tutti i feed (`get_all_feeds`), ricalcola due volte il totale dei non letti con un'altra copia e ricarica fino a 500 articoli. `ArticleListModel._apply_filter` (`ui/models.py:272`) fa sempre `beginResetModel`.
- Prova: **un solo** "segna come letto" tramite navigazione ha causato **2 reset** del modello. Il primo arriva dall'evento `item_read_changed`, il secondo da `_deliver_command`.
- Anche `ui/window.py:126` fa `sync()` a ogni `WindowActivate`, cioè a ogni alt-tab.
- `core/site_icon_service.py:311` esegue un `glob` sul filesystem per ogni feed a ogni ricostruzione della sidebar, nel thread GUI.
- Sospetto da verificare a schermo: i reset fanno saltare lo scroll della lista mentre l'utente legge.
- **Correzione:** un solo `sync` per mutazione, aggiornamenti mirati con `dataChanged` sul modello articoli (come già fa `SourceListModel.replace`) e icone tenute in cache in memoria.

**M5. Codice morto e strati di "compatibilità" mai usati in produzione**: [CODICE] (riferimenti contati con grep)
- `core/feed_http.py:242` `fetch_url`, `:247` `fetch_url_simple`: 0 usi.
- `core/feed_fetcher.py:95` `fetch_and_parse` e `:35` `FeedFetchResult.__iter__` ("vecchio unpacking a tre valori"); `core/feed_manager.py:225` `_normalize_fetch_result` gestisce tuple che nessuno restituisce più. Restano in vita solo grazie ai test.
- `core/feed_manager.py:523` `rename_feed` e `:549` `set_category`, sostituiti da `update_feed`; `:621` `get_feeds_by_category`. Usati solo dai test.
- `core/app_controller.py:237-296`: dieci wrapper sincroni (`add_feed`, `remove_feed`, `get_recent_items`, `mark_read`, `rename_feed`, `set_category`, `update_feed`, `get_feeds_by_category`, `get_items_by_category`, `get_all_items`). La UI usa le varianti `*_async`; questi servono solo ai test. Anche `settings_manager` (`:106`), `is_refreshing` (`:138`) e `stop_auto_refresh` (`:452`) non hanno usi in produzione.
- `core/models.py:154` `FeedCategory`, `core/item_identity.py:95` `legacy_link_id`, `core/exceptions.py:56` `UIError`: inutilizzati.
- `config/constants.py`: `Shortcuts` (`:114`; le scorciatoie sono scritte a mano in `Main.qml:39-48`, che ha anche `Ctrl+O`, assente nella classe), `REFRESH_INTERVAL_SECONDS` (`:70`), `CARD_PADDING`/`CARD_MARGIN`/`CARD_BORDER_RADIUS`, `MAX_GRID_COLUMNS` e i quattro `*_FONT_SIZE` di `UIConstraints` (`:103-111`), `NEWS_VIEW_MIN_WIDTH`, `AppMeta.DESCRIPTION`: inutilizzati.
- `ui/controller.py:668` e `:688-690`: `feed_removed` e `feed_updated` compaiono in due rami e il secondo non viene mai raggiunto per loro. `feed_renamed` e `feed_category_changed` non vengono più emessi in produzione.
- **Correzione:** eliminare questi simboli e riscrivere i test che li usano sulle API reali (`update_feed`, `*_async`).

**M6. `core/__init__.py` importa l'intero grafo applicativo e annulla il bootstrap dell'allocatore**: [ESEGUITO]
- `main.py:11` importa `core.native_memory` "prima degli import pesanti". Python esegue però prima `core/__init__.py`, che importa `AppController`, `requests`, `feedparser` e il resto (88 ms misurati con `-X importtime`). Subito dopo `bootstrap_allocator()` esegue `execve` e il nuovo processo rifà tutti gli import.
- Nessun modulo di produzione usa la "superficie pubblica" di `core/__init__.py`.
- **Correzione:** svuotare `core/__init__.py` (e, per coerenza, `config/__init__.py` e `ui/__init__.py`).

**M7. Circa un quarto dei test è grep del sorgente, non test di comportamento**: [ESEGUITO] (conteggio con AST)
- 57 test su 227 funzioni leggono file sorgente e cercano stringhe letterali, senza eseguire codice. Si concentrano in `tests/test_core/test_architecture_contracts.py`, `tests/test_ui/test_qml_ui.py`, `tests/test_ui/test_memory_contracts.py`, `tests/test_ui/test_signal_sync.py`, `tests/test_installation.py` e `tests/test_release_workflow.py`.
- Esempi: `assert "model: [1, 5, 15, 30, 60, 120, 360]" in dialogs_source` e `assert main.count("cacheBuffer: 0") >= 2`. Altri test verificano che file cancellati da tempo (`event_bus.py`, `ui/web`, `bridge.py`) non esistano.
- Questi test bloccano qualsiasi refactoring (rinominare una variabile li fa fallire) e non trovano bug: nessuno di loro rileva A1–A3 o M1–M4.
- I test comportamentali (core, HTTP con server locale, E2E QML) sono invece buoni e vanno tenuti.
- **Correzione:** eliminare i test di archeologia. Sostituire quelli che proteggono un vincolo reale (per esempio "il core non importa Qt") con controlli AST sugli import, e gli altri con test di comportamento.

**M8. Dipendenze: viene installato WebEngine (~270 MB) che il README dice di non usare**: [ESEGUITO]
- `requirements.txt:2` usa il metapacchetto `PySide6`, che installa `PySide6_WebEngine` (265 MB) e `PySide6_Pdf` (6 MB). A runtime serve solo `PySide6_Essentials` (QtQuick, Effects, Svg, plugin ico), che contiene anche lo script `pyside6-qsb`. Il binario `qsb` sta però in `PySide6_Addons` ed è necessario solo per compilare lo shader.
- **Correzione:** `PySide6-Essentials` + `PySide6-Addons` (vincolo `==` tra le due versioni), da verificare con `install.sh` ed E2E. Alzare `pytest` a `<10` per il CVE.

### Gravità bassa

- **B1. SIGINT/`Ctrl+C` non chiude l'app** [ESEGUITO]: l'event loop Qt non restituisce mai il controllo all'handler Python. *Correzione:* `signal.signal(SIGINT, lambda *_: app.quit())` più un `QTimer` periodico di qualche centinaio di ms.
- **B2. Traceback completo nel log a ogni errore DNS o di rete** [ESEGUITO]: `core/feed_http.py:229-235` usa `exc_info=True` a livello WARNING. Nella prova un feed rotto ha prodotto un traceback di circa 40 righe al minuto. *Correzione:* `exc_info` solo a livello DEBUG.
- **B3. Notifica "N nuovi articoli" al primo aggiornamento di un feed appena aggiunto** [CODICE]: `replace_items` considera nuovi tutti gli articoli, quindi la notifica annuncia 20–50 "nuovi" articoli. *Correzione:* non emettere `new_items_available` quando la sorgente non aveva articoli.
- **B4. `last_error` non viene persistito** [ESEGUITO]: `core/feed_manager.py:377` lo salva solo in memoria e dopo un riavvio i feed rotti risultano "Mai aggiornato". È coerente con il punto A1, ma va deciso esplicitamente.
- **B5. Costanti duplicate tra Python e QML** [CODICE]: minimo 900×600, default 1280×800 e sidebar 240–480 compaiono sia in `config/constants.py` sia in `ui/qml/Main.qml:8-10, 24, 70, 288-306`. *Correzione:* esporle da `PreferencesAdapter` o accettare QML come unica fonte.
- **B6. Docstring e README non allineati** [CODICE]:
  - `config/__init__.py:4` cita `ui/web/styles.css`, che non esiste; `ui/tray.py:1` parla di "web-based desktop UI"; `ui/native_actions.py:1` parla di "WebChannel bridge".
  - Il README (`README.md:111-145`) elenca solo 8 dei 16 moduli di `core/` (mancano `diagnostics`, `exceptions`, `feed_http`, `feed_link_extractor`, `feed_parser`, `feed_serializer`, `item_identity`, `models`) e 10 dei 13 file QML (mancano `ModalSurface`, `NeuTextField`, `Toast`, oltre a `qmldir`). Chiama inoltre la root `news_aggregator/`.
  - `core/diagnostics.py:9` dichiara di non leggere tutto il file, ma lo scorre per intero.
- **B7. `AppMeta.AUTHOR = "CachyOS User"` usato come `organizationName`** [CODICE] (`main.py:65`): è un segnaposto.
- **B8. User-Agent `Chrome/121` contro impersonificazione `chrome120`** [CODICE] (`config/constants.py:84`, `core/feed_http.py:192`): incoerenza minore.
- **B9. Cronologia git sporca** [ESEGUITO]: commit `noop`, `placeholder`, `SHOULD_NOT`, `tmp_should_not_exist` e i relativi revert. Non c'è niente di pericoloso e non vale la pena riscrivere la storia.

### Verificato e in ordine (non serve intervenire)

- Nessun segreto o token nel codice o nella cronologia git (`git log -p` su tutti i rami); il workflow di release usa solo `github.token`.
- Gli URL aggiunti dall'utente sono validati (solo http/https, `ui/controller.py:705-714`) e anche l'apertura dei link nel browser (`ui/native_actions.py`). Ho provato `file://` nel fetcher: bloccato.
- Tutto il testo QML è `Text.PlainText`, quindi un feed non può iniettare HTML o immagini remote.
- Le scritture di impostazioni e catalogo sono atomiche (file temporaneo più `replace`). Le impostazioni sono validate per tipo e intervallo, e i JSON corrotti non bloccano l'avvio.
- Il menu del tray sopravvive al garbage collector (verificato).
- Il servizio favicon ha limiti di dimensione, cache negativa e accetta solo http/https.

---

## 3. Complessità che probabilmente non serve

Questi punti vanno valutati, non sono errori:

- **Ottimizzazioni di memoria native** (`core/native_memory.py`, il riavvio di sé tramite `execve` in `main.py`, `malloc_trim` dopo ogni aggiornamento, il rilascio delle risorse Qt nel tray). Sono molto codice e molti test-contratto, per un guadagno mai misurato in modo comparativo (lo dice anche `docs/audit-2026-09-29.md`). `execve` cambia inoltre il PID e perde le opzioni dell'interprete. Proposta: misurare la RSS con e senza su un caso reale, poi decidere. [SOSPETTO] che il beneficio sia trascurabile.
- **Epoch delle sorgenti e copy-on-write dell'intero catalogo** (`core/feed_manager.py`). Proteggono da corse reali (rimozione durante un aggiornamento), ma a costo O(catalogo) per ogni clic. Se la persistenza passa a SQLite o a scritture con debounce, si semplificano molto.
- **Due stack HTTP** (`feed_http` per i feed, `requests` diretto in `site_icon_service`) con politiche diverse su limiti, User-Agent e fallback. Un solo modulo HTTP con limite di dimensione riduce duplicazione e incoerenze (vedi M3).
- **Tre eccezioni base su due moduli** (`config/exceptions.py` e `core/exceptions.py`, che reimporta e riesporta). Si può unificare, ma l'impatto è basso.

---

## 4. Piano di pulizia

Le fasi sono ordinate dalla più sicura e utile alla più invasiva. Al termine di ogni fase la suite completa deve restare verde.

| Fase | Contenuto | Rischio | Sforzo stimato |
|---|---|---|---|
| **1. Bug funzionali piccoli** | A2 (aggiornamento all'avvio e default a 15–30 min), A3 (conservare `published`), M1 (toast solo su azione manuale o cambio di stato), A1 nella parte minima (niente persistenza sul 304), B1 (SIGINT), B2 (log senza traceback), B3 (niente notifica al primo fetch). Ogni correzione con un test di comportamento | Basso | ½ giornata |
| **2. Rimozione del codice morto** | M5 e M6: API compatibili, wrapper sincroni, `rename_feed`/`set_category`, costanti e classi inutilizzate, rami irraggiungibili, `__init__.py` svuotati, docstring WebEngine (B6). Riscrittura dei test che usano i simboli rimossi | Basso | ½–1 giornata (è la parte più lunga per via dei test) |
| **3. Robustezza della rete** | M2 (fallback `curl` solo su 403/challenge, al massimo 5 candidati dallo stesso dominio, niente azzeramento della cache sugli errori di rete), M3 (limite di dimensione condiviso con le favicon), unificazione del modulo HTTP | Medio-basso | ½–1 giornata |
| **4. Dipendenze, installazione e documentazione** | M8 (`PySide6-Essentials` + `Addons`, `pytest<10`), aggiornamento della struttura nel README, B7/B8, eventuale aggiunta di Python 3.14 alla matrice CI | Basso | 2–3 ore |
| **5. Pulizia dei test** | M7: eliminare i test di archeologia e quelli che fanno grep di stringhe, sostituire i vincoli architetturali con controlli AST sugli import, aggiungere test di comportamento per i punti delle fasi 1 e 3 | Basso (solo test) | ½ giornata |
| **6. Persistenza e sincronizzazione della UI** | A1 completo (scrittore con debounce o SQLite), M4 (un solo sync per mutazione, aggiornamenti mirati del modello articoli, cache delle icone in memoria), semplificazione del copy-on-write del catalogo. Decisione misurata su `native_memory`/`execve` | Medio-alto (tocca lo stato canonico e la concorrenza) | 2–3 giornate |

Note sull'ordine:

- Le fasi 1 e 2 si possono anche invertire. Fare prima la fase 2 riduce la superficie da toccare, ma la fase 1 porta subito benefici visibili.
- La fase 5 conviene **prima** della fase 6, perché i test che fanno grep del sorgente bloccherebbero il refactoring della UI.
- La fase 6 è l'unica in cui ha senso riscrivere un pezzo (lo strato di persistenza) invece di correggerlo.

---

## 5. Esito della pulizia (19 novembre 2026)

Tutte e sei le fasi sono state eseguite sul branch `cleanup/analisi-fasi`, nell'ordine 2 → 5 → 1 → 3 → 6 → 4: prima la riduzione della superficie, poi le correzioni coperte da test di comportamento, per ultime dipendenze e documentazione. Nessun commit è stato creato.

**Verifica finale [ESEGUITO]:** su un'installazione pulita da `install.sh` passano `compileall`, `bash -n`, `qmllint` e `pip check`, e `pip-audit` non segnala vulnerabilità note. Passano tutti i **211 test** (core ed E2E offscreen), sia con pytest 9.2 sia sulla `.venv` migrata. È stata anche avviata l'app reale con 8 feed veri più uno rotto.

| Fase | Fatto | Punti chiusi |
|---|---|---|
| 2 | Rimosse le API "compatibili", i wrapper sincroni, `rename_feed`/`set_category`/`get_feeds_by_category`, le costanti e classi inutilizzate e i rami irraggiungibili. Gli `__init__.py` ora contengono solo la docstring; corrette le docstring dell'era WebEngine. Il filtro per feed e il conteggio dei non letti stanno in `FeedManager`, senza copie | M5, M6, B6 (docstring) |
| 5 | Eliminati circa 55 test che facevano grep del sorgente. `tests/test_architecture.py` controlla i confini degli import via AST e il PlainText del QML; `tests/http_fakes.py` simula le risposte in streaming | M7 |
| 1 | Refresh all'avvio (`AppController.start()`), intervallo predefinito di 15 min, data originale conservata per gli articoli senza data, niente toast per i fallimenti di singoli feed in background, nessuna scrittura sui 304 invariati, niente notifica al primo fetch, `Ctrl+C`/SIGTERM con shutdown pulito, log senza traceback | A2, A3, M1, B1, B2, B3 |
| 3 | Fallback `curl_cffi` solo su 403/503, challenge o errore TLS; limite di 10 MB sui feed con lettore condiviso con le favicon (che ora chiudono sempre le connessioni); discovery ferma sugli errori di rete; al massimo 5 candidati http(s), e per gli `<a>` solo dello stesso sito; `FeedFetchError.status_code`; cache dell'URL risolto conservata sugli errori temporanei | M2, M3, B8 |
| 6 | Persistenza a due velocità (transazionale per le modifiche al catalogo, differita per refresh e "letto", una scrittura per refresh globale, flush garantito alla chiusura). Nella UI: un solo sync per mutazione, "letto" aggiornato riga per riga, nuovi articoli inseriti in cima senza reset, niente sync a ogni alt-tab, favicon in cache in memoria. Rimossi `native_memory`/`execve`/`malloc_trim` dopo la misura | A1, M4, §3 |
| 4 | `PySide6-Essentials` + `PySide6-Addons` al posto del metapacchetto (`.venv` pulita da 492 MB), migrazione automatica delle `.venv` esistenti in `install.sh`, `pytest<10`, matrice CI su Python 3.12 e 3.14, README riscritto dove non corrispondeva più al codice, rimosso il segnaposto `AUTHOR` | M8, B6, B7 |

**Misura che ha deciso la rimozione di `native_memory` [ESEGUITO]:** RSS dell'app reale dopo il refresh di 8 feed, due esecuzioni per configurazione.

| Configurazione | RSS |
|---|---|
| Arena glibc limitati a 2 (comportamento precedente) | 153,7–154,2 MB |
| Arena a 64 | 156,1–157,9 MB |
| Senza `malloc_trim` | 153,6–154,1 MB |

Il guadagno è di circa 2–4 MB su 155 (circa 2%): non giustifica il riavvio del processo con `execve` né il modulo dedicato.

**Non chiuso, per scelta:**
- **B4:** `last_error` resta solo in memoria.
- **B5:** le costanti dimensionali restano duplicate tra Python e QML.
- **B9:** la cronologia git non è stata riscritta.
- Le due gerarchie di eccezioni (`config/` e `core/`) restano separate perché `config/` non può importare `core/`.

**Da sapere:**
- Chi ha già un `settings.json` mantiene l'intervallo salvato (prima il default era 1 minuto): va cambiato dalle preferenze.
- Su una `.venv` esistente basta rilanciare `./install.sh`.
- Gli E2E sono stati eseguiti in locale con `offscreen`; Xvfb/xcb e la matrice 3.14 verranno esercitati dalla CI al primo push.
