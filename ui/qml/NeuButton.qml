import QtQuick
import "."

Item {
    id: root
    property string label: ""
    property bool accent: false
    property real cornerRadius: Theme.radiusMD
    property int textSize: 15
    signal clicked()

    implicitWidth: 42
    implicitHeight: 42
    activeFocusOnTab: root.enabled
    Accessible.role: Accessible.Button
    Accessible.name: root.label
    Accessible.focusable: root.enabled
    Accessible.pressed: tap.pressed
    Accessible.onPressAction: if (root.enabled) root.clicked()
    opacity: root.enabled ? 1.0 : 0.42
    scale: tap.pressed ? 0.985 : 1.0
    Behavior on scale { NumberAnimation { duration: 85; easing.type: Easing.OutCubic } }

    RaisedSurface {
        anchors.fill: parent
        soft: true
        hovered: hover.hovered && root.enabled
        selected: root.accent && !tap.pressed
        cornerRadius: root.cornerRadius
        visible: !tap.pressed
    }
    InsetSurface {
        anchors.fill: parent
        cornerRadius: root.cornerRadius
        active: root.accent || root.activeFocus
        depth: 6.0
        visible: tap.pressed
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: Math.max(1, root.cornerRadius - 2)
        color: "transparent"
        border.width: root.activeFocus ? 1 : 0
        border.color: root.activeFocus ? Theme.accentLine : "transparent"
    }
    Text {
        anchors.centerIn: parent
        width: Math.max(0, parent.width - 12)
        y: tap.pressed ? 1 : 0
        text: root.label
        color: root.accent ? Theme.accent : (hover.hovered ? Theme.textPrimary : Theme.textSecondary)
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(root.textSize * Theme.fontScale)
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        Behavior on color { ColorAnimation { duration: 110 } }
    }
    HoverHandler { id: hover; enabled: root.enabled }
    TapHandler { id: tap; enabled: root.enabled; cursorShape: Qt.PointingHandCursor; onTapped: root.clicked() }
    Keys.onSpacePressed: if (root.enabled) root.clicked()
    Keys.onReturnPressed: if (root.enabled) root.clicked()
}
