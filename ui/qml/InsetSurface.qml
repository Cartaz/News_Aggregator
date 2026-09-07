import QtQuick
import QtQuick.Effects
import "."

Item {
    id: root
    property real cornerRadius: Theme.radiusMD
    property bool active: false
    property color surfaceColor: Theme.surface
    property real depth: 7.0
    default property alias content: contentItem.data

    RectangularShadow {
        anchors.fill: insetShader
        visible: root.active
        radius: root.cornerRadius
        blur: 10
        spread: -1
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlow
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
        property color accentColor: Theme.accentGlowStrong
        property real stateActive: root.active ? 1.0 : 0.0
        fragmentShader: "shaders/neumorphic_inset.frag.qsb"
    }
    Item { id: contentItem; anchors.fill: parent }
}
