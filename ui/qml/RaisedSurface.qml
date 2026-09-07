import QtQuick
import QtQuick.Effects
import "."

Item {
    id: root
    property real cornerRadius: Theme.radiusLG
    property bool soft: false
    property bool selected: false
    property bool hovered: false
    property color surfaceColor: Theme.surface
    property bool cacheShadows: false
    default property alias content: contentItem.data

    readonly property real darkOffset: soft ? (hovered ? 4.5 : 3.5) : 8
    readonly property real lightOffset: soft ? (hovered ? -3.8 : -3.0) : -6
    readonly property real darkBlur: soft ? (hovered ? 12 : 10) : 20
    readonly property real lightBlur: soft ? (hovered ? 10 : 8.5) : 15

    RectangularShadow {
        anchors.fill: body
        radius: root.cornerRadius
        blur: root.darkBlur
        spread: root.soft ? -0.5 : 0
        offset: Qt.vector2d(root.darkOffset, root.darkOffset)
        color: root.soft ? Theme.raisedDarkSoft : Theme.raisedDark
        cached: root.cacheShadows
        Behavior on blur { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
    RectangularShadow {
        anchors.fill: body
        radius: root.cornerRadius
        blur: root.lightBlur
        spread: root.soft ? -0.4 : 0
        offset: Qt.vector2d(root.lightOffset, root.lightOffset)
        color: root.soft ? Theme.raisedLightSoft : Theme.raisedLight
        cached: root.cacheShadows
        Behavior on blur { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
    RectangularShadow {
        anchors.fill: body
        visible: root.selected
        radius: root.cornerRadius
        blur: 11
        spread: -1
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlow
        cached: false
    }
    Rectangle {
        id: body
        anchors.fill: parent
        radius: root.cornerRadius
        color: root.surfaceColor
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? Theme.accentLine : "transparent"
        antialiasing: true
    }
    Item { id: contentItem; anchors.fill: body }
}
