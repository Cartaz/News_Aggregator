# Patch GUI — News Aggregator

Questa patch corregge i problemi di GUI evidenziati dallo screenshot
analizzato (sidebar con testo troncato, colonne mal dimensionate,
mancanza di separazione visiva tra lista e dettaglio, allineamento
non ottimale di colonne numeriche).

## File modificati

| File | Modifica |
|------|----------|
| `ui/widgets/source_list.py` | Colonna "Sorgente" in `Stretch` (riempie lo spazio disponibile, niente più troncamento di "Tutti gli articoli"); colonna "Da leggere" in `ResizeToContents` con minimo 64px; scrollbar orizzontale sempre off; header default alignment left. |
| `ui/widgets/source_tree_builder.py` | Allineamento a destra (`AlignRight \| AlignVCenter`) per i contatori "Da leggere" di tutti i nodi (radice, categorie, sorgenti). |
| `ui/widgets/news_view.py` | Larghezza colonna Data 100px e Ora 70px (miglior respiro); colonna Sorgente ridotta da 160→150px; `setMinimumSectionSize(80)`; header Data/Ora centrato via `setHeaderData(TextAlignmentRole)`; pannello dettaglio con property `detailPanel=True` per applicare bordo superiore; padding dettaglio aumentato a `12,10,12,4`; splitter sizes `420,220`. |
| `ui/widgets/news_view_table.py` | `setTextAlignment(AlignCenter)` sulle celle Data e Ora per allineamento coerente con le intestazioni. |
| `ui/styles/neumorphism.py` | Scrollbarvertical/horizontal da 10px→12px (più visibili); nuovo selettore `QWidget[detailPanel="true"]` con `border-top` per separazione netta tra tabella articoli e dettaglio. |
| `ui/main_window.py` | Larghezza minima `SourceList` da 180→240px; `setSizes([320, 940])` invece di `[260, 1000]` per dare più spazio alla sidebar. |
| `config/constants.py` | `SOURCE_LIST_MAX_WIDTH` da 360→480px per permettere sidebar più larga se l'utente la trascina. |

## Problemi risolti (mappati all'analisi dello screenshot)

1. **".tti gli articoli" troncato a sinistra** — La colonna 0 era fissa a
   220px ma la sidebar era larga solo ~260px: la colonna 1 (80px) "ruba"
   spazio e la colonna 0 finiva fuori viewport. Ora la colonna 0 è in
   `Stretch` mode e riempie sempre tutto lo spazio disponibile.

2. **Header "ENTE" invece di "SORGENTE"** — Stessa causa: testo
   dell'header troncato per larghezza colonna insufficiente. Ora la
   colonna 0 si adatta alla larghezza disponibile.

3. **Header "DA LEGGI…" troncato** — La colonna 1 era fissa a 80px ma
   l'header "DA LEGGERI" (uppercase + letter-spacing 0.08em) richiede
   ~85px. Ora la colonna è in `ResizeToContents` e si adatta al testo
   dell'header.

4. **Colonne Data e Ora allineate a sinistra** — Date e orari sono
   valori numerici corti: allineati al centro migliorano la leggibilità.
   Allineamento applicato sia alle celle (`setTextAlignment`) sia alle
   intestazioni (`setHeaderData` con `TextAlignmentRole`).

5. **Contatori "Da leggere" non allineati** — I conteggi numerici ora
   sono allineati a destra su tutti i nodi (radice, categoria, fonte).

6. **Mancanza di separazione tra lista articoli e dettaglio** — Aggiunto
   `border-top` sul widget contenitore del dettaglio (via property
   `detailPanel=True` + selettore QSS) per una riga di separazione netta.

7. **Sidebar troppo stretta di default** — Larghezza iniziale del
   splitter aumentata da 260→320px, minimo da 180→240px.

8. **Scrollbar troppo sottili** — Larghezza scrollbar da 10px→12px per
   migliorare la visibilità/scopribilità.

## Come applicare la patch

Estrai `patch.zip` nella root del progetto sovrascrivendo i file
esistenti:

```bash
unzip -o patch.zip -d /percorso/del/progetto/
```

Verifica l'integrità con i test esistenti:

```bash
pytest -m "not ui"          # test non-UI (non richiedono display)
pytest -m "ui"              # test UI (richiedono PySide6 + pytest-qt)
```

La patch è compatibile con i test esistenti: in particolare
`test_news_view_table_header_modes` continua a passare perché i
`ResizeMode` delle 4 colonne (Fixed, Fixed, Interactive, Stretch)
sono stati preservati.
