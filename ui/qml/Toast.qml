import QtQuick
import "."

Item {
    id: root
    property string title: ""
    property string message: ""
    property bool error: false
    property bool shown: false
    width: 330
    height: shown ? 86 : 0
    opacity: shown ? 1 : 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 140 } }
    Behavior on height { NumberAnimation { duration: 140 } }

    function show(titleText, messageText, isError) {
        root.title = titleText
        root.message = messageText
        root.error = Boolean(isError)
        root.shown = true
        hideTimer.restart()
    }

    RaisedSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; soft: true; selected: !root.error }
    Rectangle { x: 12; y: 14; width: 4; height: parent.height - 28; radius: 2; color: root.error ? Theme.textMuted : Theme.accent }
    Text { x: 26; y: 14; width: parent.width - 40; text: root.title; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(13 * Theme.fontScale); font.bold: true; elide: Text.ElideRight }
    Text { x: 26; y: 38; width: parent.width - 40; text: root.message; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Math.round(11 * Theme.fontScale); wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
    Timer { id: hideTimer; interval: 3600; onTriggered: root.shown = false }
}
