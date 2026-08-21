#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${PROJECT_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
REQUIREMENTS_FILE="${PROJECT_DIR}/requirements.txt"

cd "${PROJECT_DIR}"

info() {
    printf '==> %s\n' "$1"
}

fail() {
    printf 'Errore: %s\n' "$1" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 \
    || fail "Interprete ${PYTHON_BIN} non trovato. Installa Python 3.12 o superiore."

"${PYTHON_BIN}" - <<'PY' \
    || fail "News Aggregator richiede Python 3.12 o superiore."
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

[[ -f "${REQUIREMENTS_FILE}" ]] \
    || fail "requirements.txt non trovato in ${PROJECT_DIR}."

if [[ -d "${VENV_DIR}" && ! -x "${VENV_PYTHON}" ]]; then
    info "Ambiente virtuale incompleto: ricreo .venv"
    rm -rf "${VENV_DIR}"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    info "Creo l'ambiente virtuale .venv"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}" \
        || fail "Creazione di .venv fallita. Verifica che il modulo venv sia disponibile."
else
    info "Riutilizzo l'ambiente virtuale .venv esistente"
fi

info "Aggiorno gli strumenti di packaging"
"${VENV_PYTHON}" -m pip install --upgrade pip setuptools wheel

info "Installo le dipendenze runtime"
"${VENV_PYTHON}" -m pip install -r "${REQUIREMENTS_FILE}"

info "Verifico le dipendenze principali"
"${VENV_PYTHON}" - <<'PY'
import brotli
import curl_cffi
import feedparser
import requests
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

print("Dipendenze verificate.")
PY

printf '\nInstallazione completata.\n'
printf 'Avvio:\n  .venv/bin/python main.py\n\n'
