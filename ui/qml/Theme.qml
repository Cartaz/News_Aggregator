pragma Singleton
import QtQuick

QtObject {
    readonly property string fontFamily: "Noto Sans"
    property real fontScale: 1.0
    readonly property color surface: "#141414"
    readonly property color accent: "#ff6600"
    readonly property color textPrimary: "#e1e1e1"
    readonly property color textSecondary: "#878787"
    readonly property color textMuted: "#5a5a5a"
    readonly property color line: Qt.rgba(1, 1, 1, 0.035)
    readonly property color raisedDark: Qt.rgba(0, 0, 0, 0.62)
    readonly property color raisedDarkSoft: Qt.rgba(0, 0, 0, 0.46)
    readonly property color raisedLight: Qt.rgba(0.294, 0.294, 0.294, 0.10)
    readonly property color raisedLightSoft: Qt.rgba(0.294, 0.294, 0.294, 0.075)
    readonly property color insetDark: Qt.rgba(0, 0, 0, 0.60)
    readonly property color insetLight: Qt.rgba(0.294, 0.294, 0.294, 0.095)
    readonly property color accentGlow: Qt.rgba(1, 0.4, 0, 0.15)
    readonly property color accentGlowStrong: Qt.rgba(1, 0.4, 0, 0.24)
    readonly property color accentLine: Qt.rgba(1, 0.4, 0, 0.22)
    readonly property int radiusXL: 28
    readonly property int radiusLG: 22
    readonly property int radiusMD: 16
    readonly property int radiusSM: 12
}
