# News Aggregator — Engineering Roadmap

Questa roadmap raccoglie i miglioramenti tecnici pianificati dopo il completamento della nuova UI. L'obiettivo è migliorare prestazioni, robustezza e manutenibilità senza cambiare inutilmente l'esperienza utente.

## Regole di lavoro

- Ogni voce viene implementata in una modifica isolata e testabile.
- `main` deve restare avviabile con `.venv/bin/python main.py`.
- Nessuna nuova funzione UI viene aggiunta se non serve a una capacità reale del core.
- Le ottimizzazioni di rete devono avere fallback sicuri.
- Ogni regressione scoperta durante l'uso viene accompagnata da un test quando ragionevole.

## Fase A — Prestazioni di rete e refresh — COMPLETATA

### A1. Cache dell'URL RSS/Atom risolto — COMPLETATO
- [x] Cache persistente `resolved_feed_url`, fallback e compatibilità JSON.
- [x] Test di persistenza, uso cache e rediscovery.

### A2. HTTP condizionale (`ETag` / `Last-Modified`) — COMPLETATO
- [x] Validator persistenti, richieste condizionali e `304 Not Modified`.
- [x] Invalidazione/retry e test 200/304.

### A3. Refresh concorrente limitato — COMPLETATO
- [x] Massimo 4 worker e una task per sorgente.
- [x] Progresso completati/totale, errori isolati e shutdown pulito.
- [x] Persistenza serializzata e test di concorrenza.

## Fase B — Robustezza e qualità — COMPLETATA

### B1. Stato operativo centralizzato nel controller — COMPLETATO
- [x] Un solo `RefreshState` per refresh globale e singolo.
- [x] `AppController` sorgente di verità per stato/progresso/feed attivi.
- [x] Bridge e JavaScript ridotti a adapter/renderer.
- [x] Guard dei refresh sovrapposti nel controller e test lifecycle.

### B2. Identità e deduplicazione articoli — COMPLETATO
1. GUID stabile, se presente;
2. URL canonico normalizzato;
3. fallback `source + title + published`.

- [x] GUID persistito e normalizzazione URL/tracking.
- [x] Migrazione compatibile dei vecchi ID preservando `read`.
- [x] Deduplicazione parser/replace e test di regressione.

### B3. Test end-to-end WebEngine — COMPLETATO
- [x] Avvio reale `QWebEngineView` + `QWebChannel` in ambiente test.
- [x] Refresh globale controllato `0/N → N/N` e riabilitazione pulsante.
- [x] Filtro non letti + cambio articolo e navigazione ↑/↓.
- [x] Aggiunta, modifica e rimozione feed tramite UI reale.
- [x] Errori verificati come feedback visibile all'utente.
- [x] Test isolati dalla rete con backend/storage temporanei.

### B4. Continuous Integration — COMPLETATO
- [x] GitHub Actions su pull request e push a `main`.
- [x] Python 3.12, `pytest` e contratti statici/core.
- [x] `bash -n install.sh` e compilazione Python.
- [x] `node --check` su tutti i file JavaScript del frontend.
- [x] Job QtWebEngine separato sotto Xvfb.
- [x] Dipendenze Linux Qt/Chromium esplicite per Ubuntu runner.
- [x] Pipeline verificata realmente con entrambi i job verdi.

**Criterio di completamento Fase B:** stato operativo centralizzato, identità degli articoli robusta, flussi UI critici coperti da un vero browser Qt e ogni PR validata automaticamente prima del merge.

## Fase C — Evoluzione dello storage

### C1. Valutazione e migrazione SQLite — FUTURO
Da iniziare solo quando il JSON diventa un limite misurabile.

- [ ] Schema `feeds`, `articles`, `categories`, `http_metadata`.
- [ ] Migrazione automatica JSON → SQLite con backup.
- [ ] Indici e transazioni.
- [ ] Test di migrazione e rollback.
- [ ] Nessuna perdita dello stato letto/non letto.

### C2. Ricerca backend / FTS — FUTURO
Dipende da C1.

- [ ] Ricerca titolo, fonte, sommario e autore.
- [ ] Valutazione SQLite FTS5.
- [ ] Query paginata dal frontend invece di caricare grandi dataset in memoria.

## Fase D — Rifiniture UX non urgenti

- [ ] `Home` / `End` per primo/ultimo articolo.
- [ ] Valutare `Enter` per aprire l'articolo selezionato nel browser.
- [ ] `Page Up` / `Page Down` solo se utile nell'uso reale.
- [ ] Vista/aiuto discreto delle scorciatoie da tastiera.
- [ ] Indicazione opzionale del feed corrente durante il refresh, senza appesantire la UI.

## Ordine di esecuzione

1. A1 — cache URL feed risolto ✅
2. A2 — ETag / Last-Modified ✅
3. A3 — refresh concorrente limitato ✅
4. B1 — stato refresh centralizzato ✅
5. B2 — deduplicazione robusta ✅
6. B3 — test end-to-end ✅
7. B4 — CI ✅
8. pausa di utilizzo e misurazione
9. C1/C2 solo se giustificati dai dati
10. D in base all'uso reale
