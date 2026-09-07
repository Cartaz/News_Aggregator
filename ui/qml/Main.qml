import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import "."

Window {
    id: root
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: false
    color: Theme.surface
    title: backend.appName

    property real sidebarWidth: Math.max(240, Math.min(480, backend.preferences.sidebarWidth))
    property real sidebarDragStartWidth: sidebarWidth

    Component.onCompleted: Theme.fontScale = backend.preferences.fontScaleFactor

    function showToast(title, message, error) { toast.show(title, message, error) }

    Shortcut { sequence: "Ctrl+F"; enabled: !dialogs.opened; onActivated: searchInput.forceActiveFocus() }
    Shortcut { sequence: "Ctrl+N"; enabled: !dialogs.opened; onActivated: dialogs.openAddFeed() }
    Shortcut { sequence: "Ctrl+R"; enabled: !dialogs.opened; onActivated: backend.refreshAll() }
    Shortcut { sequence: "Ctrl+Shift+R"; enabled: !dialogs.opened; onActivated: backend.refreshSelectedFeed() }
    Shortcut { sequence: "Ctrl+D"; enabled: !dialogs.opened; onActivated: dialogs.openRemoveFeed() }
    Shortcut { sequence: "Ctrl+O"; enabled: !dialogs.opened; onActivated: backend.openSelectedArticle() }
    Shortcut { sequence: "Ctrl+M"; enabled: !dialogs.opened; onActivated: backend.markSelectedRead() }
    Shortcut { sequence: "Ctrl+H"; enabled: !dialogs.opened; onActivated: backend.hideApp() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: backend.quitApp() }
    Shortcut { sequence: "Escape"; enabled: dialogs.opened; onActivated: dialogs.closeDialog() }

    Connections {
        target: backend
        function onToastRequested(title, message, error) { root.showToast(title, message, error) }
        function onArticleSelectionChanged() {
            if (backend.selectedArticleRow >= 0 && articleList.currentIndex !== backend.selectedArticleRow)
                articleList.currentIndex = backend.selectedArticleRow
        }
        function onSelectedSourceChanged() {
            if (sourceList.currentIndex !== backend.selectedSourceRow)
                sourceList.currentIndex = backend.selectedSourceRow
            if (backend.selectedSourceRow >= 0)
                sourceList.positionViewAtIndex(backend.selectedSourceRow, ListView.Contain)
        }
    }

    Connections {
        target: backend.preferences
        function onChanged() {
            Theme.fontScale = backend.preferences.fontScaleFactor
            if (!sidebarDrag.active)
                root.sidebarWidth = Math.max(240, Math.min(480, backend.preferences.sidebarWidth))
        }
        function onSidebarPersistFailed(message) {
            root.showToast("Larghezza sidebar non salvata", message, true)
        }
    }

    Item {
        id: appShell
        anchors.fill: parent
        anchors.margins: 20
        enabled: !dialogs.opened

        ColumnLayout {
            anchors.fill: parent
            spacing: 18

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusLG }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 18
                    spacing: 18

                    RowLayout {
                        Layout.preferredWidth: 245
                        spacing: 13
                        Item {
                            Layout.preferredWidth: 42; Layout.preferredHeight: 42
                            InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; active: true; depth: 6.4 }
                            Text { anchors.centerIn: parent; text: "N"; color: Theme.accent; font.family: Theme.fontFamily; font.pixelSize: Math.round(19 * Theme.fontScale); font.bold: true }
                        }
                        Column {
                            spacing: 1
                            Text { text: backend.appName; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(16 * Theme.fontScale); font.weight: Font.DemiBold }
                            Text { text: backend.scopeTitle; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); elide: Text.ElideRight; width: 185 }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; active: searchInput.activeFocus; depth: 6.3 }
                        Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: "⌕"; color: searchInput.activeFocus ? Theme.accent : Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(18 * Theme.fontScale) }
                        TextInput {
                            id: searchInput
                            objectName: "searchInput"
                            x: 40; width: parent.width - 104; height: parent.height
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.textPrimary; selectionColor: Theme.accent; selectedTextColor: Theme.surface
                            font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale); clip: true
                            activeFocusOnTab: true
                            Accessible.role: Accessible.EditableText
                            Accessible.name: "Cerca negli articoli"
                            Accessible.editable: true
                            Accessible.searchEdit: true
                            Accessible.focusable: true
                            onTextEdited: backend.setSearchQuery(text)
                        }
                        Text { x: 40; anchors.verticalCenter: parent.verticalCenter; visible: searchInput.text.length === 0 && !searchInput.activeFocus; text: "Cerca titolo, fonte o testo…"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale) }
                        RaisedSurface {
                            width: 48; height: 25
                            anchors.right: parent.right; anchors.rightMargin: 9; anchors.verticalCenter: parent.verticalCenter
                            cornerRadius: 12; soft: true
                            Text { anchors.centerIn: parent; text: "Ctrl F"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(9 * Theme.fontScale); font.weight: Font.DemiBold }
                        }
                    }

                    NeuButton { Layout.preferredWidth: 42; Layout.preferredHeight: 42; label: backend.refreshing ? "…" : "↻"; enabled: !backend.refreshing; onClicked: backend.refreshAll() }
                    NeuButton { Layout.preferredWidth: 42; Layout.preferredHeight: 42; label: "⚙"; accent: true; onClicked: dialogs.openSettings() }
                }

                Item {
                    id: refreshTrack
                    visible: backend.refreshing && backend.refreshScope === "all"
                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                    anchors.leftMargin: 22; anchors.rightMargin: 22; anchors.bottomMargin: 6
                    height: 4
                    Accessible.role: Accessible.ProgressBar
                    Accessible.name: "Progresso aggiornamento feed"
                    Accessible.description: backend.refreshCurrent + " di " + backend.refreshTotal + " feed aggiornati"

                    Row {
                        id: refreshSegments
                        anchors.fill: parent
                        spacing: backend.refreshTotal > 1 ? 3 : 0
                        Repeater {
                            model: backend.refreshTotal
                            Rectangle {
                                required property int index
                                width: Math.max(0, (refreshSegments.width - refreshSegments.spacing * Math.max(0, backend.refreshTotal - 1)) / Math.max(1, backend.refreshTotal))
                                height: refreshSegments.height
                                radius: 2
                                color: index < backend.refreshCurrent ? Theme.accent : Qt.rgba(0, 0, 0, 0.45)
                                Behavior on color { ColorAnimation { duration: 140 } }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                Item {
                    Layout.preferredWidth: root.sidebarWidth
                    Layout.minimumWidth: 240
                    Layout.maximumWidth: 480
                    Layout.fillHeight: true
                    RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 17
                        spacing: 9

                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 48
                            Column {
                                Text { text: "RACCOLTA"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); font.bold: true; font.letterSpacing: 1.2 }
                                Text { text: "Sorgenti"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(19 * Theme.fontScale); font.weight: Font.DemiBold }
                            }
                            Item { Layout.fillWidth: true }
                            NeuButton { Layout.preferredWidth: 42; Layout.preferredHeight: 42; label: "+"; accent: true; onClicked: dialogs.openAddFeed() }
                        }

                        ListView {
                            id: sourceList
                            objectName: "sourceList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 2
                            model: backend.sources
                            reuseItems: true
                            boundsBehavior: Flickable.StopAtBounds
                            currentIndex: backend.selectedSourceRow
                            delegate: SourceRow {
                                width: ListView.view.width
                                onClicked: { sourceList.currentIndex = index; backend.selectSource(index) }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: backend.selectedSourceIsFeed ? 92 : 0
                            visible: backend.selectedSourceIsFeed
                            InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; depth: 6.0 }
                            Column {
                                anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { width: parent.width; text: backend.selectedSourceTitle; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); font.bold: true; elide: Text.ElideRight }
                                Text { width: parent.width; text: backend.selectedSourceStatus; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); elide: Text.ElideRight }
                                Row {
                                    spacing: 6
                                    NeuButton { width: 74; height: 30; label: "Aggiorna"; textSize: 10; enabled: !backend.refreshing; onClicked: backend.refreshSelectedFeed() }
                                    NeuButton { width: 70; height: 30; label: "Modifica"; textSize: 10; onClicked: dialogs.openEditFeed() }
                                    NeuButton { width: 68; height: 30; label: "Rimuovi"; textSize: 10; onClicked: dialogs.openRemoveFeed() }
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.preferredWidth: 6
                    Layout.fillHeight: true
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Separator
                    Accessible.name: "Ridimensiona pannello sorgenti"
                    Accessible.focusable: true
                    InsetSurface { anchors.fill: parent; cornerRadius: 3; depth: 3.2 }
                    Rectangle { anchors.centerIn: parent; width: 1; height: 42; color: parent.activeFocus ? Theme.accent : Theme.textMuted }
                    Keys.onLeftPressed: {
                        root.sidebarWidth = Math.max(240, root.sidebarWidth - 16)
                        backend.preferences.setSidebarWidth(Math.round(root.sidebarWidth))
                    }
                    Keys.onRightPressed: {
                        root.sidebarWidth = Math.min(480, root.sidebarWidth + 16)
                        backend.preferences.setSidebarWidth(Math.round(root.sidebarWidth))
                    }
                    DragHandler {
                        id: sidebarDrag
                        target: null
                        xAxis.enabled: true
                        cursorShape: Qt.SplitHCursor
                        onActiveChanged: {
                            if (active) root.sidebarDragStartWidth = root.sidebarWidth
                            else backend.preferences.setSidebarWidth(Math.round(root.sidebarWidth))
                        }
                        onTranslationChanged: {
                            if (active)
                                root.sidebarWidth = Math.max(240, Math.min(480, root.sidebarDragStartWidth + translation.x))
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 14

                    Item {
                        Layout.fillWidth: true; Layout.preferredHeight: 70
                        RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusLG; soft: true }
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18
                            Column {
                                Text { text: "VISTA CORRENTE"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); font.bold: true; font.letterSpacing: 1.2 }
                                Text { text: backend.scopeTitle; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(18 * Theme.fontScale); font.weight: Font.DemiBold; elide: Text.ElideRight; width: 320 }
                                Text { text: backend.visibleArticleCount === backend.totalArticleCount ? (backend.totalArticleCount + (backend.totalArticleCount === 1 ? " articolo" : " articoli")) : (backend.visibleArticleCount + " di " + backend.totalArticleCount + " articoli"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                            }
                            Item { Layout.fillWidth: true }
                            Text { text: "Solo non letti"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale) }
                            NeuToggle {
                                Layout.preferredWidth: 46; Layout.preferredHeight: 26
                                checked: backend.unreadOnly
                                accessibleName: "Solo non letti"
                                onToggled: function(value) { backend.setUnreadOnly(value) }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 16

                        Item {
                            Layout.preferredWidth: 390
                            Layout.fillHeight: true
                            RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                            ListView {
                                id: articleList
                                objectName: "articleList"
                                anchors.fill: parent; anchors.margins: 12
                                clip: true; spacing: 0
                                model: backend.articles
                                currentIndex: backend.selectedArticleRow
                                reuseItems: true; cacheBuffer: 0
                                boundsBehavior: Flickable.StopAtBounds
                                keyNavigationEnabled: true
                                activeFocusOnTab: true
                                highlightFollowsCurrentItem: true
                                highlightMoveDuration: 120
                                highlightResizeDuration: 90
                                highlight: Item {
                                    width: articleList.width; height: 76
                                    InsetSurface { anchors.fill: parent; anchors.margins: 2; cornerRadius: Theme.radiusSM; active: true; depth: 6.0 }
                                }
                                delegate: ArticleRow {
                                    width: ListView.view.width
                                    selected: ListView.isCurrentItem
                                    onClicked: { articleList.currentIndex = index; backend.selectArticle(index); articleList.forceActiveFocus() }
                                }
                                onCurrentIndexChanged: {
                                    if (activeFocus && currentIndex >= 0 && currentIndex !== backend.selectedArticleRow)
                                        backend.selectArticle(currentIndex)
                                }
                            }

                            Column {
                                anchors.centerIn: parent
                                spacing: 8
                                visible: backend.visibleArticleCount === 0
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "▤"; color: Theme.textMuted; font.pixelSize: Math.round(28 * Theme.fontScale) }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Nessun articolo da mostrare"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale); font.bold: true }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Aggiorna i feed o modifica i filtri."; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 32
                                spacing: 14
                                visible: backend.hasSelectedArticle
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: backend.selectedArticleSource; color: Theme.accent; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale); font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: backend.selectedArticleDate; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                                }
                                Text { Layout.fillWidth: true; text: backend.selectedArticleTitle; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(24 * Theme.fontScale); font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                                Text { text: backend.selectedArticleAuthor; visible: text.length > 0; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale) }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.line }
                                Flickable {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    clip: true; contentWidth: width; contentHeight: summaryText.height
                                    Text {
                                        id: summaryText
                                        width: parent.width
                                        text: backend.selectedArticleSummary
                                        color: Theme.textSecondary
                                        font.family: Theme.fontFamily; font.pixelSize: Math.round(14 * Theme.fontScale)
                                        lineHeight: 1.45; wrapMode: Text.WordWrap
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    NeuButton { Layout.preferredWidth: 164; Layout.preferredHeight: 42; label: "Apri nel browser"; accent: true; cornerRadius: 14; textSize: 13; enabled: backend.selectedArticleHasLink; onClicked: backend.openSelectedArticle() }
                                    NeuButton { Layout.preferredWidth: 148; Layout.preferredHeight: 42; label: backend.selectedArticleRead ? "Già letto" : "Segna come letto"; cornerRadius: 14; textSize: 13; enabled: !backend.selectedArticleRead; onClicked: backend.markSelectedRead() }
                                    Item { Layout.fillWidth: true }
                                }
                            }

                            Column {
                                anchors.centerIn: parent
                                spacing: 8
                                visible: !backend.hasSelectedArticle
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "▤"; color: Theme.textMuted; font.pixelSize: Math.round(32 * Theme.fontScale) }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Seleziona un articolo"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(14 * Theme.fontScale); font.bold: true }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Il contenuto testuale apparirà qui."; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                            }
                        }
                    }
                }
            }
        }
    }

    AppDialogs {
        id: dialogs
        anchors.fill: parent
        backend: backend
        onToastRequested: function(title, message, error) { root.showToast(title, message, error) }
    }

    Toast { id: toast; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: 24; anchors.bottomMargin: 24; z: 20 }
}
