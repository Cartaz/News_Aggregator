import QtQuick
import QtQuick.Effects
import "."

Item {
    id: root
    property url source
    property color tint: Theme.accent
    property real iconOpacity: 1.0
    readonly property bool ready: sourceImage.status === Image.Ready

    Image {
        id: sourceImage
        anchors.fill: parent
        source: root.source
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        asynchronous: true
        visible: false
    }

    MultiEffect {
        anchors.fill: sourceImage
        source: sourceImage
        visible: root.ready
        colorization: 1.0
        colorizationColor: root.tint
        opacity: root.iconOpacity
    }
}
