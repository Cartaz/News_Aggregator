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

    readonly property var appBackend: backend
    readonly property bool compactLayout: width < 1180
    readonly property bool denseLayout: width < 1020
    readonly property real shellMargin: compactLayout ? 14 : 20
    readonly property real workspaceGap: compactLayout ? 12 : 14
    readonly property real articleGap: compactLayout ? 12 : 16
    readonly property real effectiveSidebarWidth: denseLayout ? 210 : (compactLayout ? 220 : sidebarWidth)

    property real sidebarWidth: Math.max(240, Math.min(480, backend.preferences.sidebarWidth))
    property real sidebarDragStartWidth: sidebarWidth

    function updateResponsiveTypography() {
        Theme.viewportTextScale = Math.max(0.94, Math.min(1.16, 1.0 + (root.width - 1280) / 4000.0))
    }

    Component.onCompleted: {
        Theme.userFontScale = backend.preferences.fontScaleFactor
        updateResponsiveTypography()
    }
    onWidthChanged: updateResponsiveTypography()

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
            Theme.userFontScale = backend.preferences.fontScaleFactor
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
        anchors.margins: root.shellMargin
        enabled: !dialogs.opened

        ColumnLayout {
            anchors.fill: parent
            spacing: root.compactLayout ? 14 : 18

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusLG }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.compactLayout ? 16 : 20
                    anchors.rightMargin: root.compactLayout ? 14 : 18
                    spacing: root.compactLayout ? 12 : 18

                    RowLayout {
                        Layout.preferredWidth: root.denseLayout ? 174 : (root.compactLayout ? 194 : 245)
                        Layout.minimumWidth: root.denseLayout ? 164 : 180
                        spacing: 13

                        Item {
                            Layout.preferredWidth: 42
                            Layout.preferredHeight: 42
                            InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; depth: 5.2 }
                            Rectangle { anchors.fill: parent; radius: Theme.radiusMD; color: "transparent"; border.width: 1; border.color: Theme.accentLine }
                            AccentIcon {
                                anchors.centerIn: parent
                                width: 22
                                height: 22
                                source: Qt.resolvedUrl("../../assets/icons/news-aggregator.svg")
                                tint: Theme.accent
                            }
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 1
                            Text { width: parent.width; text: backend.appName; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(16 * Theme.fontScale); font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { width: parent.width; text: backend.scopeTitle; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale); elide: Text.ElideRight }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.minimumWidth: root.denseLayout ? 180 : 230
                        Layout.preferredHeight: 42
                        InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; active: searchInput.activeFocus; depth: 5.2 }
                        Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: "⌕"; color: searchInput.activeFocus ? Theme.accent : Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(18 * Theme.fontScale) }
                        TextInput {
                            id: searchInput
                            objectName: "searchInput"
                            x: 40
                            width: parent.width - (root.denseLayout ? 54 : 104)
                            height: parent.height
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.textPrimary
                            selectionColor: Theme.accent
                            selectedTextColor: Theme.surface
                            font.family: Theme.fontFamily
                            font.pixelSize: Math.round(13 * Theme.fontScale)
                            clip: true
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
                            visible: !root.denseLayout
                            width: 48
                            height: 25
                            anchors.right: parent.right
                            anchors.rightMargin: 9
                            anchors.verticalCenter: parent.verticalCenter
                            cornerRadius: 12
                            soft: true
                            Text { anchors.centerIn: parent; text: "Ctrl F"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(9 * Theme.fontScale); font.weight: Font.DemiBold }
                        }
                    }

                    NeuButton { Layout.preferredWidth: 42; Layout.preferredHeight: 42; label: backend.refreshing ? "…" : "↻"; enabled: !backend.refreshing; onClicked: backend.refreshAll() }
                    NeuButton { Layout.preferredWidth: 42; Layout.preferredHeight: 42; label: "⚙"; accent: true; onClicked: dialogs.openSettings() }
                }

                Item {
                    id: refreshTrack
                    visible: backend.refreshing && backend.refreshScope === "all"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 22
                    anchors.rightMargin: 22
                    anchors.bottomMargin: 6
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
                id: workspace
                objectName: "workspace"
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: root.workspaceGap

                Item {
                    id: sourcePanel
                    objectName: "sourcePanel"
                    Layout.preferredWidth: root.effectiveSidebarWidth
                    Layout.minimumWidth: root.effectiveSidebarWidth
                    Layout.maximumWidth: root.effectiveSidebarWidth
                    Layout.fillHeight: true
                    RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: root.compactLayout ? 15 : 17
                        spacing: 9

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 48
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
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8
                                Text { width: parent.width; text: backend.selectedSourceTitle; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale); font.bold: true; elide: Text.ElideRight }
                                Text { width: parent.width; text: backend.selectedSourceStatus; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); elide: Text.ElideRight }
                                RowLayout {
                                    width: parent.width
                                    spacing: 6
                                    NeuButton { Layout.fillWidth: true; Layout.preferredHeight: 30; label: "Aggiorna"; textSize: 10; enabled: !backend.refreshing; onClicked: backend.refreshSelectedFeed() }
                                    NeuButton { Layout.fillWidth: true; Layout.preferredHeight: 30; label: "Modifica"; textSize: 10; onClicked: dialogs.openEditFeed() }
                                    NeuButton { Layout.fillWidth: true; Layout.preferredHeight: 30; label: "Rimuovi"; textSize: 10; onClicked: dialogs.openRemoveFeed() }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: sidebarSeparator
                    Layout.preferredWidth: root.compactLayout ? 0 : 6
                    Layout.fillHeight: true
                    visible: !root.compactLayout
                    activeFocusOnTab: visible
                    Accessible.role: Accessible.Separator
                    Accessible.name: "Ridimensiona pannello sorgenti"
                    Accessible.focusable: visible
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
                    id: contentArea
                    objectName: "contentArea"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 0
                    spacing: 14

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 70
                        RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusLG; soft: true }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 18
                            anchors.rightMargin: 18
                            Column {
                                Text { text: "VISTA CORRENTE"; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); font.bold: true; font.letterSpacing: 1.2 }
                                Text { text: backend.scopeTitle; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(18 * Theme.fontScale); font.weight: Font.DemiBold; elide: Text.ElideRight; width: root.compactLayout ? 220 : 320 }
                                Text { text: backend.visibleArticleCount === backend.totalArticleCount ? (backend.totalArticleCount + (backend.totalArticleCount === 1 ? " articolo" : " articoli")) : (backend.visibleArticleCount + " di " + backend.totalArticleCount + " articoli"); color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                            }
                            Item { Layout.fillWidth: true }
                            Text { visible: !root.denseLayout; text: "Solo non letti"; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale) }
                            NeuToggle {
                                Layout.preferredWidth: 46
                                Layout.preferredHeight: 26
                                checked: backend.unreadOnly
                                accessibleName: "Solo non letti"
                                onToggled: function(value) { backend.setUnreadOnly(value) }
                            }
                        }
                    }

                    RowLayout {
                        id: articleColumns
                        objectName: "articleColumns"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: root.articleGap

                        Item {
                            id: articleListPanel
                            objectName: "articleListPanel"
                            Layout.preferredWidth: Math.max(root.denseLayout ? 270 : (root.compactLayout ? 290 : 330), Math.min(root.compactLayout ? 330 : 430, contentArea.width * (root.compactLayout ? 0.46 : 0.44)))
                            Layout.minimumWidth: root.denseLayout ? 270 : (root.compactLayout ? 290 : 330)
                            Layout.maximumWidth: root.compactLayout ? 340 : 460
                            Layout.fillHeight: true
                            RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                            ListView {
                                id: articleList
                                objectName: "articleList"
                                anchors.fill: parent
                                anchors.margins: root.compactLayout ? 10 : 12
                                clip: true
                                spacing: 0
                                model: backend.articles
                                currentIndex: backend.selectedArticleRow
                                reuseItems: true
                                cacheBuffer: 0
                                boundsBehavior: Flickable.StopAtBounds
                                keyNavigationEnabled: true
                                activeFocusOnTab: true
                                highlightFollowsCurrentItem: true
                                highlightMoveDuration: 120
                                highlightResizeDuration: 90
                                highlight: Item {
                                    width: articleList.width
                                    height: 72
                                    InsetSurface { anchors.fill: parent; anchors.margins: 2; cornerRadius: Theme.radiusSM; active: true; selected: true; depth: 6.0 }
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
                            id: detailPanel
                            objectName: "detailPanel"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: root.denseLayout ? 300 : (root.compactLayout ? 320 : 390)
                            RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusXL }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: root.compactLayout ? 22 : 32
                                spacing: root.compactLayout ? 12 : 14
                                visible: backend.hasSelectedArticle

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { Layout.maximumWidth: Math.max(120, detailPanel.width * 0.55); text: backend.selectedArticleSource; color: Theme.accent; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale); font.bold: true; elide: Text.ElideRight }
                                    Item { Layout.fillWidth: true }
                                    Text { text: backend.selectedArticleDate; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale) }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: backend.selectedArticleTitle
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Math.round(24 * Theme.fontScale)
                                    font.weight: Font.DemiBold
                                    lineHeight: 1.18
                                    wrapMode: Text.WordWrap
                                }

                                Text { text: backend.selectedArticleAuthor; visible: text.length > 0; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(12 * Theme.fontScale) }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.line }

                                Flickable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    contentWidth: width
                                    contentHeight: summaryText.height
                                    Text {
                                        id: summaryText
                                        width: parent.width
                                        text: backend.selectedArticleSummary
                                        color: Theme.textPrimary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Math.round(14 * Theme.fontScale)
                                        lineHeight: 1.6
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: childrenRect.height
                                    spacing: 10
                                    NeuButton { width: 164; height: 42; label: "Apri nel browser"; accent: true; cornerRadius: 14; textSize: 13; enabled: backend.selectedArticleHasLink; onClicked: backend.openSelectedArticle() }
                                    NeuButton { width: 148; height: 42; label: backend.selectedArticleRead ? "Già letto" : "Segna come letto"; cornerRadius: 14; textSize: 13; enabled: !backend.selectedArticleRead; onClicked: backend.markSelectedRead() }
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
        objectName: "appDialogs"
        anchors.fill: parent
        backend: root.appBackend
        onToastRequested: function(title, message, error) { root.showToast(title, message, error) }
    }

    Toast { id: toast; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: 24; anchors.bottomMargin: 24; z: 20 }
}
