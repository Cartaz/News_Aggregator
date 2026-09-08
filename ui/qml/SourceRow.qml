import QtQuick
import "."

Item {
    id: root
    required property string kind
    required property string identifier
    required property string title
    required property int unreadCount
    required property bool selected
    required property bool firstFeed
    required property string iconSource
    required property int index
    signal clicked()
    implicitHeight: 43
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: root.title
    Accessible.description: root.unreadCount + " non letti"
    Accessible.selectable: true
    Accessible.selected: root.selected
    Accessible.focusable: true
    Accessible.onPressAction: root.clicked()

    Rectangle {
        visible: root.firstFeed
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 9
        anchors.rightMargin: 9
        height: 1
        color: Theme.line
    }
    RaisedSurface {
        anchors.fill: parent
        anchors.margins: 1
        cornerRadius: Theme.radiusSM
        soft: true
        hovered: hover.hovered
        visible: !root.selected && hover.hovered
    }
    InsetSurface {
        anchors.fill: parent
        anchors.margins: 1
        cornerRadius: Theme.radiusSM
        active: root.selected || root.activeFocus
        selected: root.selected
        depth: 6.0
        visible: root.selected
    }

    AccentIcon {
        x: 11
        width: 16
        height: 16
        anchors.verticalCenter: parent.verticalCenter
        source: root.kind === "all"
            ? Qt.resolvedUrl("../../assets/icons/news-aggregator.svg")
            : root.iconSource
        visible: root.kind === "all" || (root.kind === "feed" && root.iconSource.length > 0)
        tint: Theme.accent
        iconOpacity: root.selected ? 1.0 : 0.72
    }
    Text {
        x: 12
        anchors.verticalCenter: parent.verticalCenter
        visible: root.kind === "category" || (root.kind === "feed" && root.iconSource.length === 0)
        text: root.kind === "category" ? "◇" : "▧"
        color: root.kind === "feed" ? Qt.rgba(1, 0.4, 0, root.selected ? 1.0 : 0.65) : (root.selected ? Theme.accent : Theme.textSecondary)
        font.family: Theme.fontFamily
        font.pixelSize: Math.round((root.kind === "feed" ? 14 : 12) * Theme.fontScale)
    }
    Text {
        x: 35
        width: parent.width - 84
        anchors.verticalCenter: parent.verticalCenter
        text: root.title
        elide: Text.ElideRight
        color: root.selected ? Theme.accent : (hover.hovered ? Theme.textPrimary : Theme.textSecondary)
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(13 * Theme.fontScale)
        font.weight: root.selected ? Font.DemiBold : Font.Normal
        Behavior on color { ColorAnimation { duration: 110 } }
    }
    InsetSurface {
        width: 30
        height: 23
        x: parent.width - width - 10
        anchors.verticalCenter: parent.verticalCenter
        cornerRadius: 11
        depth: 4.6
        Text {
            anchors.centerIn: parent
            text: root.unreadCount > 99 ? "99+" : String(root.unreadCount)
            color: root.selected ? Theme.accent : Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(10 * Theme.fontScale)
            font.bold: true
        }
    }
    HoverHandler { id: hover }
    TapHandler { cursorShape: Qt.PointingHandCursor; onTapped: root.clicked() }
    Keys.onSpacePressed: root.clicked()
    Keys.onReturnPressed: root.clicked()
}
