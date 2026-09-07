import QtQuick
import "."

Item {
    id: root
    property alias text: input.text
    property string placeholderText: ""
    property string label: ""
    property bool password: false
    signal accepted()
    implicitHeight: 42

    InsetSurface { anchors.fill: parent; cornerRadius: Theme.radiusMD; active: input.activeFocus; depth: 6.3 }
    TextInput {
        id: input
        activeFocusOnTab: true
        Accessible.role: Accessible.EditableText
        Accessible.name: root.label.length ? root.label : root.placeholderText
        Accessible.editable: true
        Accessible.focusable: true
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.textPrimary
        selectionColor: Theme.accent
        selectedTextColor: Theme.surface
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(13 * Theme.fontScale)
        clip: true
        echoMode: root.password ? TextInput.Password : TextInput.Normal
        onAccepted: root.accepted()
    }
    Text {
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        visible: input.text.length === 0 && !input.activeFocus
        text: root.placeholderText
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(13 * Theme.fontScale)
    }
}
