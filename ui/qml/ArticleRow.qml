import QtQuick
import "."

Item {
    id: root
    required property string itemId
    required property string sourceTitle
    required property string title
    required property string publishedRelative
    required property bool read
    required property int index
    property bool selected: false
    signal clicked()
    implicitHeight: 76
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title
    Accessible.description: root.sourceTitle + ", " + root.publishedRelative
    Accessible.selectable: true
    Accessible.selected: root.selected
    Accessible.focusable: true
    Accessible.onPressAction: root.clicked()

    RaisedSurface {
        anchors.fill: parent
        anchors.margins: 2
        cornerRadius: Theme.radiusSM
        soft: true
        hovered: hover.hovered
        visible: !root.selected
    }
    Text {
        x: 13; y: 12
        width: parent.width - 42
        text: root.title
        elide: Text.ElideRight
        color: root.selected ? Theme.accent : (root.read ? Theme.textSecondary : Theme.textPrimary)
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(13 * Theme.fontScale)
        font.weight: root.read ? Font.Normal : Font.DemiBold
    }
    Rectangle {
        visible: !root.read
        width: 7; height: 7; radius: 4
        x: parent.width - width - 13; y: 17
        color: Theme.accent
    }
    Text {
        x: 13; y: 42
        width: parent.width - 82
        text: root.sourceTitle
        elide: Text.ElideRight
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(10 * Theme.fontScale)
    }
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 13
        y: 42
        text: root.publishedRelative
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(10 * Theme.fontScale)
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        radius: Theme.radiusSM - 2
        color: "transparent"
        border.width: root.activeFocus ? 1 : 0
        border.color: root.activeFocus ? Theme.accentLine : "transparent"
    }
    HoverHandler { id: hover }
    TapHandler { cursorShape: Qt.PointingHandCursor; onTapped: root.clicked() }
    Keys.onSpacePressed: root.clicked()
    Keys.onReturnPressed: root.clicked()
}
