import QtQuick
import QtQuick.Window
import "."

Item {
    id: root
    required property var backend
    readonly property bool opened: modalMode !== ""
    property string modalMode: ""
    property bool modalBusy: false
    property int settingsInterval: backend.preferences.refreshIntervalMinutes
    property bool settingsAutoRead: backend.preferences.markReadOnSelect
    property bool settingsNotify: backend.preferences.notifyNewItems
    property bool settingsTray: backend.preferences.closeToTray
    property real settingsScale: backend.preferences.fontScaleFactor
    property var modalReturnFocus: null
    signal toastRequested(string title, string message, bool error)

    function showToast(title, message, error) { root.toastRequested(title, message, error) }
    function rememberFocus() {
        if (!root.opened && root.Window.window)
            root.modalReturnFocus = root.Window.window.activeFocusItem
    }
    function finishDialog() {
        const closingMode = root.modalMode
        root.modalBusy = false
        root.modalMode = ""
        if (closingMode === "log")
            backend.diagnostics.clear()
        const target = root.modalReturnFocus
        root.modalReturnFocus = null
        if (target) Qt.callLater(function() { target.forceActiveFocus() })
    }
    function openAddFeed() {
        rememberFocus()
        root.modalBusy = false
        root.modalMode = "add"
    }
    function openEditFeed() {
        if (!backend.selectedSourceIsFeed) return
        rememberFocus()
        root.modalBusy = false
        root.modalMode = "edit"
    }
    function openRemoveFeed() {
        if (!backend.selectedSourceIsFeed) return
        rememberFocus()
        root.modalBusy = false
        root.modalMode = "remove"
    }
    function openSettings() {
        rememberFocus()
        root.settingsInterval = backend.preferences.refreshIntervalMinutes
        root.settingsAutoRead = backend.preferences.markReadOnSelect
        root.settingsNotify = backend.preferences.notifyNewItems
        root.settingsTray = backend.preferences.closeToTray
        root.settingsScale = backend.preferences.fontScaleFactor
        root.modalBusy = false
        root.modalMode = "settings"
    }
    function openLog() {
        if (backend.diagnostics.load()) root.modalMode = "log"
    }
    function closeDialog() {
        if (root.modalBusy) return
        finishDialog()
    }

    Connections {
        target: backend
        function onOperationFinished(action, ok, message) {
            if (action === "addFeed" && root.modalMode === "add") {
                root.modalBusy = false
                if (ok) { root.finishDialog(); root.showToast("Feed aggiunto", message, false) }
                else root.showToast("Feed non aggiunto", message, true)
            } else if (action === "updateFeed" && root.modalMode === "edit") {
                root.modalBusy = false
                if (ok) { root.finishDialog(); root.showToast("Feed aggiornato", "", false) }
                else root.showToast("Modifica non salvata", message, true)
            } else if (action === "removeFeed" && root.modalMode === "remove") {
                root.modalBusy = false
                if (ok) { root.finishDialog(); root.showToast("Feed rimosso", "", false) }
                else root.showToast("Feed non rimosso", message, true)
            }
        }
    }

    Connections {
        target: backend.preferences
        function onSaveFinished(ok, message) {
            if (root.modalMode !== "settings") return
            root.modalBusy = false
            if (ok) {
                root.finishDialog()
                root.showToast("Impostazioni salvate", "", false)
            } else {
                root.showToast("Impostazioni non salvate", message, true)
            }
        }
    }

    Connections {
        target: backend.diagnostics
        function onLoadFailed(message) { root.showToast("Log non disponibile", message, true) }
    }

    Loader {
        id: modalLoader
        anchors.fill: parent
        active: root.opened
        sourceComponent: modalFrame
    }

    Component {
        id: modalFrame
        ModalSurface {
            anchors.fill: parent
            eyebrow: root.modalMode === "settings"
                ? "Preferenze"
                : (root.modalMode === "log"
                    ? "Diagnostica"
                    : (root.modalMode === "remove" ? "Conferma" : "Sorgente"))
            title: root.modalMode === "add"
                ? "Aggiungi un feed"
                : root.modalMode === "edit"
                    ? "Modifica feed"
                    : root.modalMode === "remove"
                        ? "Rimuovi feed"
                        : root.modalMode === "settings"
                            ? "Impostazioni"
                            : root.modalMode === "log"
                                ? "Log applicazione"
                                : ""
            onCloseRequested: root.closeDialog()

            Loader {
                anchors.fill: parent
                sourceComponent: root.modalMode === "add"
                    ? addBody
                    : root.modalMode === "edit"
                        ? editBody
                        : root.modalMode === "remove"
                            ? removeBody
                            : root.modalMode === "settings"
                                ? settingsBody
                                : root.modalMode === "log"
                                    ? logBody
                                    : null
            }
        }
    }

    Component {
        id: addBody
        Item {
            anchors.fill: parent
            Component.onCompleted: Qt.callLater(function() { addUrl.forceActiveFocus() })
            Column {
                anchors.fill: parent
                spacing: 14
                Text { text: "URL del feed o del sito"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                NeuTextField { id: addUrl; width: parent.width; label: "URL del feed o del sito"; placeholderText: "https://example.com/feed.xml"; onAccepted: addTitle.forceActiveFocus() }
                Text { text: "Titolo personalizzato"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                NeuTextField { id: addTitle; width: parent.width; label: "Titolo personalizzato"; placeholderText: "Opzionale" }
                Text { width: parent.width; text: "Se il sito espone un feed RSS/Atom diretto, usa quell’indirizzo."; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale); wrapMode: Text.WordWrap }
                Item { width: 1; height: 10 }
                Row {
                    anchors.right: parent.right
                    spacing: 10
                    NeuButton { width: 110; height: 42; label: "Annulla"; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: root.closeDialog() }
                    NeuButton { width: 140; height: 42; label: root.modalBusy ? "Aggiungo…" : "Aggiungi feed"; accent: true; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: { root.modalBusy = true; backend.addFeed(addUrl.text, addTitle.text) } }
                }
            }
        }
    }

    Component {
        id: editBody
        Item {
            anchors.fill: parent
            Component.onCompleted: {
                editTitle.text = backend.selectedSourceTitle
                editCategory.text = backend.selectedSourceCategory
                Qt.callLater(function() { editTitle.forceActiveFocus() })
            }
            Column {
                anchors.fill: parent
                spacing: 14
                Text { text: "Titolo"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                NeuTextField { id: editTitle; width: parent.width; label: "Titolo" }
                Text { text: "Categoria"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                NeuTextField { id: editCategory; width: parent.width; label: "Categoria"; placeholderText: "Es. Tecnologia" }
                Text { width: parent.width; text: backend.selectedSourceUrl; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); wrapMode: Text.WrapAnywhere }
                Item { width: 1; height: 10 }
                Row {
                    anchors.right: parent.right
                    spacing: 10
                    NeuButton { width: 110; height: 42; label: "Annulla"; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: root.closeDialog() }
                    NeuButton { width: 110; height: 42; label: root.modalBusy ? "Salvo…" : "Salva"; accent: true; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: { root.modalBusy = true; backend.updateSelectedFeed(editTitle.text, editCategory.text) } }
                }
            }
        }
    }

    Component {
        id: removeBody
        Item {
            anchors.fill: parent
            Column {
                anchors.fill: parent
                spacing: 20
                Text { width: parent.width; text: "Rimuovere “" + backend.selectedSourceTitle + "” e gli articoli salvati associati a questa sorgente?"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale); wrapMode: Text.WordWrap }
                Row {
                    anchors.right: parent.right
                    spacing: 10
                    NeuButton { width: 110; height: 42; label: "Annulla"; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: root.closeDialog() }
                    NeuButton { width: 110; height: 42; label: root.modalBusy ? "Rimuovo…" : "Rimuovi"; accent: true; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: { root.modalBusy = true; backend.removeSelectedFeed() } }
                }
            }
        }
    }

    Component {
        id: settingsBody
        Item {
            anchors.fill: parent
            Column {
                anchors.fill: parent
                spacing: 12
                Text { text: "Aggiornamento automatico"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale); font.bold: true }
                Row {
                    spacing: 6
                    Repeater {
                        model: [1, 5, 15, 30, 60, 120, 360]
                        NeuButton {
                            required property int modelData
                            width: 58; height: 34; cornerRadius: 12; textSize: 11
                            label: modelData < 60 ? modelData + "m" : (modelData / 60) + "h"
                            accent: root.settingsInterval === modelData
                            onClicked: root.settingsInterval = modelData
                        }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                Row {
                    width: parent.width; spacing: 12
                    Text { width: parent.width - 60; text: "Segna letto quando cambi articolo"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); anchors.verticalCenter: parent.verticalCenter }
                    NeuToggle { checked: root.settingsAutoRead; accessibleName: "Segna letto quando cambi articolo"; onToggled: function(v) { root.settingsAutoRead = v } }
                }
                Row {
                    width: parent.width; spacing: 12
                    Text { width: parent.width - 60; text: "Notifiche desktop per nuovi articoli"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); anchors.verticalCenter: parent.verticalCenter }
                    NeuToggle { checked: root.settingsNotify; accessibleName: "Notifiche desktop per nuovi articoli"; onToggled: function(v) { root.settingsNotify = v } }
                }
                Row {
                    width: parent.width; spacing: 12
                    Text { width: parent.width - 60; text: "Chiudi la finestra nel tray"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); anchors.verticalCenter: parent.verticalCenter }
                    NeuToggle { checked: root.settingsTray; accessibleName: "Chiudi la finestra nel tray"; onToggled: function(v) { root.settingsTray = v } }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                Row {
                    width: parent.width; spacing: 10
                    Text { width: 180; text: "Dimensione testo"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); anchors.verticalCenter: parent.verticalCenter }
                    NeuButton { width: 36; height: 32; label: "−"; onClicked: root.settingsScale = Math.max(0.75, Math.round((root.settingsScale - 0.05) * 100) / 100) }
                    InsetSurface { width: 70; height: 32; cornerRadius: 12; Text { anchors.centerIn: parent; text: Math.round(root.settingsScale * 100) + "%"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) } }
                    NeuButton { width: 36; height: 32; label: "+"; onClicked: root.settingsScale = Math.min(1.5, Math.round((root.settingsScale + 0.05) * 100) / 100) }
                    Item { width: 18; height: 1 }
                    NeuButton { width: 90; height: 34; label: "Apri log"; textSize: 11; onClicked: root.openLog() }
                }
                Item { width: 1; height: 12 }
                Row {
                    anchors.right: parent.right
                    spacing: 10
                    NeuButton { width: 110; height: 42; label: "Annulla"; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: root.closeDialog() }
                    NeuButton { width: 110; height: 42; label: root.modalBusy ? "Salvo…" : "Salva"; accent: true; cornerRadius: 14; textSize: 13; enabled: !root.modalBusy; onClicked: { root.modalBusy = true; backend.preferences.saveSettings(root.settingsInterval, root.settingsAutoRead, root.settingsNotify, root.settingsTray, root.settingsScale) } }
                }
            }
        }
    }

    Component {
        id: logBody
        Item {
            anchors.fill: parent
            Column {
                anchors.fill: parent
                spacing: 10
                Text { width: parent.width; text: backend.diagnostics.path; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); elide: Text.ElideMiddle }
                InsetSurface {
                    width: parent.width; height: parent.height - 70; cornerRadius: Theme.radiusMD; depth: 6.0
                    Flickable {
                        anchors.fill: parent; anchors.margins: 12; clip: true
                        contentWidth: width; contentHeight: logTextEdit.height
                        TextEdit {
                            id: logTextEdit
                            width: parent.width
                            text: backend.diagnostics.text.length ? backend.diagnostics.text : "Il log è vuoto."
                            color: Theme.textSecondary; font.family: "monospace"; font.pixelSize: Math.round(10 * Theme.fontScale)
                            wrapMode: TextEdit.WrapAnywhere; readOnly: true; selectByMouse: true
                        }
                    }
                }
                Row {
                    anchors.right: parent.right
                    spacing: 10
                    NeuButton {
                        width: 100; height: 38; label: "Copia"; textSize: 12
                        onClicked: {
                            logTextEdit.selectAll()
                            logTextEdit.copy()
                            logTextEdit.deselect()
                            root.showToast("Log copiato", "", false)
                        }
                    }
                    NeuButton { width: 100; height: 38; label: "Chiudi"; textSize: 12; onClicked: root.finishDialog() }
                }
            }
        }
    }
}
