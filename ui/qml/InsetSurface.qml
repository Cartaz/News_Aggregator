import QtQuick
import QtQuick.Effects
import "."

Item {
    id: root
    property real cornerRadius: Theme.radiusMD
    property bool active: false
    property bool selected: false
    property color surfaceColor: Theme.surface
    property real depth: 7.0
    default property alias content: contentItem.data

    RectangularShadow {
        anchors.fill: insetShader
        visible: root.active && !root.selected
        radius: root.cornerRadius
        blur: 9
        spread: -1
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlowSoft
        cached: false
    }
    RectangularShadow {
        anchors.fill: insetShader
        visible: root.selected
        radius: root.cornerRadius
        blur: 7
        spread: -0.4
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlow
        cached: false
    }
    RectangularShadow {
        anchors.fill: insetShader
        visible: root.selected
        radius: root.cornerRadius
        blur: 14
        spread: -1
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlowSoft
        cached: false
    }
    ShaderEffect {
        id: insetShader
        anchors.fill: parent
        property size itemSize: Qt.size(width, height)
        property real radiusPx: root.cornerRadius
        property real depthPx: root.depth
        property color surfaceColor: root.surfaceColor
        property color shadowDark: Theme.insetDark
        property color shadowLight: Theme.insetLight
        property color accentColor: root.selected ? Theme.accentGlow : Theme.accentGlowSoft
        property real stateActive: (root.active || root.selected) ? 1.0 : 0.0
        fragmentShader: "shaders/neumorphic_inset.frag.qsb"
    }
    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        color: "transparent"
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? Theme.accentBorder : "transparent"
        antialiasing: true
    }
    Item { id: contentItem; anchors.fill: parent }
}
