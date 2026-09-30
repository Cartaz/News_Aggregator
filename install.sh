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

run_privileged() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        fail "Noto Sans non è installato e servono privilegi amministrativi per installarlo."
    fi
}

noto_sans_available() {
    command -v fc-match >/dev/null 2>&1 \
        && fc-match -f '%{family}\n' 'Noto Sans' 2>/dev/null | head -n 1 | grep -qi 'Noto Sans'
}

ensure_noto_sans() {
    if noto_sans_available; then
        info "Font Noto Sans disponibile"
        return
    fi

    info "Installo il font UI Noto Sans"
    if command -v pacman >/dev/null 2>&1; then
        run_privileged pacman -S --needed --noconfirm noto-fonts
    elif command -v apt-get >/dev/null 2>&1; then
        run_privileged apt-get install -y fonts-noto-core
    elif command -v dnf >/dev/null 2>&1; then
        run_privileged dnf install -y google-noto-sans-fonts
    else
        fail "Noto Sans non trovato. Installa Noto Sans con il package manager della distribuzione e rilancia ./install.sh."
    fi

    if command -v fc-cache >/dev/null 2>&1; then
        fc-cache -f >/dev/null 2>&1 || true
    fi
    noto_sans_available || fail "Noto Sans risulta ancora non disponibile dopo l'installazione."
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 \
    || fail "Interprete ${PYTHON_BIN} non trovato. Installa Python 3.12 o superiore."

"${PYTHON_BIN}" - <<'PY' \
    || fail "News Aggregator richiede Python 3.12 o superiore."
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

[[ -f "${REQUIREMENTS_FILE}" ]] || fail "requirements.txt non trovato in ${PROJECT_DIR}."
[[ -f "${SHADER_SOURCE}" ]] || fail "Shader QML sorgente non trovato: ${SHADER_SOURCE}."

ensure_noto_sans

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

QSB="${VENV_DIR}/bin/pyside6-qsb"
[[ -x "${QSB}" ]] || fail "pyside6-qsb abbinato al runtime non trovato. Reinstalla PySide6 nella .venv."

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

info "Verifico caricamento QML con dati temporanei"
QT_QPA_PLATFORM=offscreen "${VENV_PYTHON}" - <<'PY'
import os
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(prefix="news-aggregator-install-") as temporary:
    for kind in ("CONFIG", "DATA", "STATE"):
        os.environ[f"XDG_{kind}_HOME"] = str(Path(temporary) / kind.lower())
    from PySide6.QtWidgets import QApplication
    from core.app_controller import AppController
    from ui.controller import UiController
    from ui.window import QmlMainWindow

    app = QApplication([])
    controller = AppController()
    ui = UiController(controller)
    try:
        window = QmlMainWindow(controller, ui)
        window.shutdown()
        print("Main.qml verificato.")
    finally:
        ui.shutdown()
        controller.shutdown()
PY

printf '\nInstallazione completata.\n'
printf 'Avvio:\n  .venv/bin/python main.py\n\n'
