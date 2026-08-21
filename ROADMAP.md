# News Aggregator — Engineering Roadmap

Questa roadmap raccoglie i miglioramenti tecnici pianificati dopo il completamento della nuova UI. L'obiettivo è migliorare prestazioni, robustezza e manutenibilità senza cambiare inutilmente l'esperienza utente.

## Regole di lavoro

- Ogni voce viene implementata in una modifica isolata e testabile.
- `main` deve restare avviabile con `.venv/bin/python main.py`.
- Nessuna nuova funzione UI viene aggiunta se non serve a una capacità reale del core.
- Le ottimizzazioni di rete devono avere fallback sicuri.
- Ogni regressione scoperta durante l'uso viene accompagnata da un test quando ragionevole.

## Fase A — Prestazioni di rete e refresh

### A1. Cache dell'URL RSS/Atom risolto — COMPLETATO

**Obiettivo:** evitare di scaricare la homepage e rifare l'auto-discovery a ogni refresh.

- [x] Aggiungere alla sorgente un `resolved_feed_url` persistente.
- [x] Usare direttamente il feed risolto nei refresh successivi.
- [x] Se il feed cached fallisce, invalidare la cache e rifare l'auto-discovery dall'URL originale.
- [x] Aggiornare automaticamente la cache quando viene scoperto un nuovo URL valido.
- [x] Mantenere compatibilità con i file JSON esistenti.
- [x] Aggiungere test di persistenza, uso cache e fallback.

**Criterio di completamento:** dopo il primo refresh di una homepage, i refresh successivi non devono richiedere nuovamente la homepage finché il feed risolto resta valido.

### A2. HTTP condizionale (`ETag` / `Last-Modified`) — COMPLETATO

- [x] Persistenza dei validator HTTP per sorgente/feed risolto.
- [x] Invio di `If-None-Match` / `If-Modified-Since`.
- [x] Gestione `304 Not Modified` senza parsing inutile.
- [x] Invalidazione validator quando cambia `resolved_feed_url`.
- [x] Retry non condizionale se un server rifiuta validator precedentemente validi.
- [x] Test con risposte 200/304, persistenza e validator cambiati.

**Criterio di completamento:** quando un server supporta validator HTTP, un feed invariato deve poter completare il refresh con `304 Not Modified` senza trasferire né riparsare il documento RSS/Atom.

### A3. Refresh concorrente limitato — PROSSIMO

- [ ] Pool conservativo di 3–4 worker.
- [ ] Nessun doppio refresh della stessa sorgente.
- [ ] Progresso globale ancora espresso come feed completati / feed totali.
- [ ] Errori isolati per sorgente.
- [ ] Shutdown pulito dei worker.
- [ ] Test su successo, errore e progresso fuori ordine.

## Fase B — Robustezza e qualità

### B1. Stato operativo centralizzato nel controller — PIANIFICATO

- [ ] Un solo modello di stato per refresh globale e singolo feed.
- [ ] `AppController` sorgente di verità per `active/current/total`.
- [ ] `WebBridge` ridotto a adapter/serializzatore.
- [ ] Eliminare duplicazioni di stato tra controller, bridge e JavaScript.

### B2. Identità e deduplicazione articoli — PIANIFICATO

Strategia prevista:

1. GUID stabile del feed, se presente;
2. URL canonico normalizzato;
3. fallback hash `source + title + published`.

- [ ] Conservare GUID RSS/Atom nel parsing.
- [ ] Normalizzare URL e parametri di tracking quando sicuro.
- [ ] Migrazione compatibile degli ID già salvati.
- [ ] Test per feed che cambiano link/GUID tra refresh.

### B3. Test end-to-end WebEngine — PIANIFICATO

- [ ] Avvio reale `QWebEngineView` in ambiente test.
- [ ] Refresh globale `0/N → N/N` e riabilitazione pulsante.
- [ ] Filtro non letti + cambio articolo.
- [ ] Navigazione tastiera ↑/↓.
- [ ] Aggiunta/modifica/rimozione feed principali.
- [ ] Test degli errori mostrati all'utente.

### B4. Continuous Integration — PIANIFICATO

- [ ] GitHub Actions su push/PR.
- [ ] `pytest`.
- [ ] controllo sintassi Python.
- [ ] `node --check` frontend.
- [ ] test installer e contratti UI.
- [ ] eventuale job WebEngine headless separato.

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

## Ordine di esecuzione previsto

1. A1 — cache URL feed risolto ✅
2. A2 — ETag / Last-Modified ✅
3. A3 — refresh concorrente limitato
4. B1 — stato refresh centralizzato
5. B2 — deduplicazione robusta
6. B3 — test end-to-end
7. B4 — CI
8. pausa di utilizzo e misurazione
9. C1/C2 solo se giustificati dai dati
10. D in base all'uso reale
