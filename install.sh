#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${PROJECT_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
REQUIREMENTS_FILE="${PROJECT_DIR}/requirements.txt"
SHADER_SOURCE="${PROJECT_DIR}/ui/qml/shaders/neumorphic_inset.frag"
SHADER_PACKAGE="${SHADER_SOURCE}.qsb"

cd "${PROJECT_DIR}"

info() { printf '==> %s\n' "$1"; }
fail() { printf 'Errore: %s\n' "$1" >&2; exit 1; }

command -v "${PYTHON_BIN}" >/dev/null 2>&1 \
    || fail "Interprete ${PYTHON_BIN} non trovato. Installa Python 3.12 o superiore."

"${PYTHON_BIN}" - <<'PY' \
    || fail "News Aggregator richiede Python 3.12 o superiore."
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

[[ -f "${REQUIREMENTS_FILE}" ]] || fail "requirements.txt non trovato in ${PROJECT_DIR}."
[[ -f "${SHADER_SOURCE}" ]] || fail "Shader QML sorgente non trovato: ${SHADER_SOURCE}."

if [[ -d "${VENV_DIR}" && ! -x "${VENV_PYTHON}" ]]; then
    info "Ambiente virtuale incompleto: ricreo .venv"
    rm -rf "${VENV_DIR}"
fi
if [[ -x "${VENV_PYTHON}" ]] && ! "${VENV_PYTHON}" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
then
    info "Ambiente virtuale creato con Python troppo vecchio: ricreo .venv"
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

QSB=""
for candidate in \
    "${VENV_DIR}/bin/pyside6-qsb" \
    "$(command -v pyside6-qsb 2>/dev/null || true)" \
    "$(command -v qsb 2>/dev/null || true)" \
    "/usr/lib/qt6/bin/qsb" \
    "/usr/lib/qt6/libexec/qsb"
do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
        QSB="${candidate}"
        break
    fi
done
[[ -n "${QSB}" ]] || fail "Compilatore shader qsb non trovato. Reinstalla PySide6 o, su Arch/CachyOS, installa qt6-shadertools."

info "Compilo lo shader neumorfico Qt Quick"
"${QSB}" --qt6 -o "${SHADER_PACKAGE}" "${SHADER_SOURCE}" \
    || fail "Compilazione shader QSB fallita."
[[ -s "${SHADER_PACKAGE}" ]] || fail "Il pacchetto shader QSB non è stato generato."
QSB_DUMP="$("${QSB}" -d "${SHADER_PACKAGE}")"
grep -q "GLSL" <<<"${QSB_DUMP}" || fail "Il pacchetto QSB non contiene una variante GLSL."

info "Verifico runtime Qt Quick e dipendenze principali"
"${VENV_PYTHON}" - <<'PY'
import brotli
import curl_cffi
import feedparser
import requests
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QSystemTrayIcon
print("Dipendenze verificate.")
PY

printf '\nInstallazione completata.\n'
printf 'Avvio:\n  .venv/bin/python main.py\n\n'
