import QtQuick
import QtQuick.Effects
import "."

Item {
    id: root
    property bool checked: true
    property string accessibleName: "Interruttore"
    signal toggled(bool checked)
    implicitWidth: 46
    implicitHeight: 26
    activeFocusOnTab: true
    Accessible.role: Accessible.Switch
    Accessible.name: root.accessibleName
    Accessible.checkable: true
    Accessible.checked: root.checked
    Accessible.focusable: true
    Accessible.onPressAction: root.toggle()
    Accessible.onToggleAction: root.toggle()

    InsetSurface { anchors.fill: parent; cornerRadius: 13; active: root.checked || root.activeFocus; depth: 6.0 }
    RaisedSurface {
        id: thumb
        width: 18; height: 18
        x: root.checked ? 24 : 4
        y: 4
        cornerRadius: 9
        soft: true
        hovered: hover.hovered
        Behavior on x { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
    }
    RectangularShadow {
        anchors.fill: dot
        visible: root.checked
        radius: 5; blur: 8; spread: -0.5
        offset: Qt.vector2d(0, 0)
        color: Theme.accentGlowStrong
    }
    Rectangle {
        id: dot
        anchors.centerIn: thumb
        width: 9; height: 9; radius: 5
        color: root.checked ? Theme.accent : Theme.textMuted
        Behavior on color { ColorAnimation { duration: 130 } }
    }
    function toggle() { root.checked = !root.checked; root.toggled(root.checked) }
    HoverHandler { id: hover }
    TapHandler { cursorShape: Qt.PointingHandCursor; onTapped: root.toggle() }
    Keys.onSpacePressed: root.toggle()
    Keys.onReturnPressed: root.toggle()
}
