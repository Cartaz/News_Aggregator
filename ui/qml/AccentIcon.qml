import QtQuick
import QtQuick.Window
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
        sourceSize: Qt.size(
            Math.max(1, Math.ceil(root.width * Screen.devicePixelRatio)),
            Math.max(1, Math.ceil(root.height * Screen.devicePixelRatio))
        )
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: false
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
