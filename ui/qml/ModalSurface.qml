import QtQuick
import "."

Item {
    id: root
    property string eyebrow: ""
    z: 10
    property string title: ""
    signal closeRequested()
    default property alias content: body.data

    Rectangle { anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.56) }
    focus: visible
    Accessible.role: Accessible.Dialog
    Accessible.name: root.title

    TapHandler {
        onTapped: (eventPoint, button) => {
            const local = root.mapToItem(panel, eventPoint.position.x, eventPoint.position.y)
            if (local.x < 0 || local.y < 0 || local.x > panel.width || local.y > panel.height)
                root.closeRequested()
        }
    }

    RaisedSurface {
        id: panel
        width: Math.min(620, parent.width - 80)
        height: Math.min(650, parent.height - 80)
        anchors.centerIn: parent
        cornerRadius: Theme.radiusXL
        Column {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 18

            Item {
                width: parent.width; height: 52
                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text { text: root.eyebrow.toUpperCase(); color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Math.round(10 * Theme.fontScale); font.bold: true; font.letterSpacing: 1.2 }
                    Text { text: root.title; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Math.round(21 * Theme.fontScale); font.weight: Font.DemiBold }
                }
                NeuButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 38; height: 38; label: "×"; onClicked: root.closeRequested() }
            }

            Item {
                id: body
                width: parent.width
                height: parent.height - 70
            }
        }
    }
}
