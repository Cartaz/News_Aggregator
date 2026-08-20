#!/usr/bin/env bash
# install.sh — Installazione locale di News Aggregator per CachyOS / Arch Linux
#
# Crea il venv, installa le dipendenze Python, installa il file .desktop
# con percorsi assoluti nel campo Exec, e copia l'icona SVG nella cache
# icone utente (~/.local/share/icons/hicolor/scalable/apps/).
#
# Conforme alle regole di Appendice H.3 del system prompt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="news-aggregator"
APP_DISPLAY="News Aggregator"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Installazione ${APP_DISPLAY}"
echo "    Directory progetto: ${SCRIPT_DIR}"
echo "    Interprete Python:  ${PYTHON_BIN}"

# --- Guardia obbligatoria (Appendice H.3) ---
# Il progetto NON deve risiedere dentro ~/.local/share/applications/
if [[ "${SCRIPT_DIR}" == "${HOME}/.local/share/applications"* ]]; then
    echo "ERRORE: Il progetto si trova dentro ~/.local/share/applications/"
    echo "   Quella directory è riservata ai soli file .desktop."
    echo "   Sposta il progetto in una cartella dedicata, ad esempio:"
    echo "     mv \"${SCRIPT_DIR}\" ~/apps/${APP_NAME}"
    exit 1
fi

# --- 1. Ambiente virtuale ---
echo "==> Creazione ambiente virtuale .venv"
if [[ ! -d "${SCRIPT_DIR}/.venv" ]]; then
    "${PYTHON_BIN}" -m venv "${SCRIPT_DIR}/.venv"
fi
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
echo "    Python venv: ${VENV_PYTHON}"

# --- 2. Dipendenze ---
echo "==> Installazione dipendenze da requirements.txt"
"${VENV_PYTHON}" -m pip install --upgrade pip --quiet
"${VENV_PYTHON}" -m pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet

# --- 3. Directory XDG ---
echo "==> Creazione directory utente"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
CONFIG_DIR="${HOME}/.config/${APP_NAME}"
DATA_DIR="${HOME}/.local/share/${APP_NAME}"
STATE_DIR="${HOME}/.local/state/${APP_NAME}"
mkdir -p "${DESKTOP_DIR}" "${ICON_DIR}" "${CONFIG_DIR}" "${DATA_DIR}" "${STATE_DIR}"

# --- 4. Icona SVG ---
echo "==> Installazione icona SVG"
ICON_SRC="${SCRIPT_DIR}/assets/icons/${APP_NAME}.svg"
if [[ -f "${ICON_SRC}" ]]; then
    cp "${ICON_SRC}" "${ICON_DIR}/${APP_NAME}.svg"
else
    echo "WARN: Icona SVG non trovata in ${ICON_SRC}"
fi

# --- 5. File .desktop con percorsi assoluti (heredoc) ---
echo "==> Generazione file .desktop con percorsi assoluti"
MAIN_SCRIPT="${SCRIPT_DIR}/main.py"
cat > "${DESKTOP_DIR}/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Version=1.5
Type=Application
Name=${APP_DISPLAY}
Name[it]=${APP_DISPLAY}
Name[en]=${APP_DISPLAY}
Comment=Aggregatore di feed RSS/Atom in formato solo testo
Comment[it]=Aggregatore di feed RSS/Atom in formato solo testo
Comment[en]=Text-only RSS/Atom feed aggregator
Exec=${VENV_PYTHON} ${MAIN_SCRIPT}
Icon=${APP_NAME}
Terminal=false
Categories=Network;News;Qt;
StartupWMClass=${APP_DISPLAY}
Keywords=rss;atom;feed;news;aggregator;
EOF

# --- 6. Aggiornamento cache desktop e icone ---
echo "==> Aggiornamento cache desktop e icone"
update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "==> Installazione completata."
echo ""
echo "    Avvia l'applicazione da menu applicazioni KDE (cerca \"${APP_DISPLAY}\"),"
echo "    oppure direttamente con:"
echo "      ${VENV_PYTHON} ${MAIN_SCRIPT}"
echo ""
echo "    File di configurazione: ${CONFIG_DIR}/settings.json"
echo "    File dati feed:          ${DATA_DIR}/feeds.json"
echo "    Log:                     ${STATE_DIR}/app.log"
