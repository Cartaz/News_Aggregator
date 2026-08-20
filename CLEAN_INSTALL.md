# News Aggregator — installazione pulita

Questa cartella contiene direttamente tutti i sorgenti necessari. Non serve
applicare patch, refactor script o installer intermedi.

## Requisiti

- Python compatibile con `requirements.txt`
- ambiente desktop con Qt/PySide6 supportato

## Installazione da zero

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Verifica

```bash
.venv/bin/python -m compileall -q main.py config core ui tests
.venv/bin/pytest tests
```

## Avvio

```bash
.venv/bin/python main.py
```

La UI include direttamente il presentation layer Dark Neumorphism con accento
`#FF6600`. Non sono inclusi installer, patcher o script di migrazione.
