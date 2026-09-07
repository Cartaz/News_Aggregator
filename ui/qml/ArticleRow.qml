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

    implicitHeight: 72
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title
    Accessible.description: root.sourceTitle + ", " + root.publishedRelative
    Accessible.selectable: true
    Accessible.selected: root.selected
    Accessible.focusable: true
    Accessible.onPressAction: root.clicked()

    Rectangle {
        visible: root.index > 0 && !root.selected
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        height: 1
        color: Theme.line
    }

    Rectangle {
        visible: hover.hovered && !root.selected
        x: 2
        y: 10
        width: 3
        height: parent.height - 20
        radius: 2
        color: Theme.accent
        opacity: 0.28
        Behavior on opacity { NumberAnimation { duration: 110 } }
    }

    Text {
        x: 12
        y: 11
        width: parent.width - 40
        text: root.title
        elide: Text.ElideRight
        color: root.selected ? Theme.accent : (root.read ? Theme.textSecondary : Theme.textPrimary)
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(13 * Theme.fontScale)
        font.weight: root.read ? Font.Normal : Font.DemiBold
    }

    Rectangle {
        visible: !root.read
        width: 7
        height: 7
        radius: 4
        x: parent.width - width - 12
        y: 17
        color: Theme.accent
    }

    Text {
        x: 12
        y: 40
        width: parent.width - 78
        text: root.sourceTitle
        elide: Text.ElideRight
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(10 * Theme.fontScale)
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 12
        y: 40
        text: root.publishedRelative
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(10 * Theme.fontScale)
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: Theme.radiusSM
        color: "transparent"
        border.width: root.activeFocus ? 1 : 0
        border.color: root.activeFocus ? Theme.accentLine : "transparent"
    }

    HoverHandler { id: hover }
    TapHandler { cursorShape: Qt.PointingHandCursor; onTapped: root.clicked() }
    Keys.onSpacePressed: root.clicked()
    Keys.onReturnPressed: root.clicked()
}
