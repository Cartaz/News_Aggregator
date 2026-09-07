pragma Singleton
import QtQuick

QtObject {
    readonly property var availableFontFamilies: Qt.fontFamilies()
    readonly property var preferredFontFamilies: [
        "Inter",
        "IBM Plex Sans",
        "Source Sans 3",
        "Fira Sans",
        "Roboto",
        "Ubuntu",
        "Cantarell",
        "Noto Sans",
        "DejaVu Sans",
        "Liberation Sans",
        "Open Sans",
        "Lato",
        "Montserrat",
        "Manrope",
        "Poppins"
    ]
    readonly property var fontChoices: buildFontChoices()
    property string userFontFamily: "Inter"
    readonly property string fallbackFontFamily: availableFontFamilies.indexOf("Noto Sans") >= 0
        ? "Noto Sans"
        : (availableFontFamilies.length > 0 ? availableFontFamilies[0] : "sans-serif")
    readonly property string fontFamily: availableFontFamilies.indexOf(userFontFamily) >= 0
        ? userFontFamily
        : fallbackFontFamily

    function isUsefulUiFont(family) {
        const lowered = family.toLowerCase()
        return lowered.indexOf("mono") === -1
            && lowered.indexOf("emoji") === -1
            && lowered.indexOf("symbol") === -1
            && lowered.indexOf("math") === -1
            && lowered.indexOf("dingbat") === -1
            && lowered.indexOf("icon") === -1
    }

    function buildFontChoices() {
        const choices = []
        for (let i = 0; i < preferredFontFamilies.length && choices.length < 10; ++i) {
            const family = preferredFontFamilies[i]
            if (availableFontFamilies.indexOf(family) >= 0 && choices.indexOf(family) < 0)
                choices.push(family)
        }
        for (let i = 0; i < availableFontFamilies.length && choices.length < 10; ++i) {
            const family = availableFontFamilies[i]
            if (isUsefulUiFont(family) && choices.indexOf(family) < 0)
                choices.push(family)
        }
        return choices.slice(0, 10)
    }

    property real userFontScale: 1.0
    property real viewportTextScale: 1.0
    readonly property real fontScale: userFontScale * viewportTextScale

    readonly property color surface: "#141414"
    readonly property color accent: "#ff6600"
    readonly property color textPrimary: "#e1e1e1"
    readonly property color textSecondary: "#878787"
    readonly property color textMuted: "#5a5a5a"
    readonly property color line: Qt.rgba(1, 1, 1, 0.04)

    readonly property color raisedDark: Qt.rgba(0, 0, 0, 0.64)
    readonly property color raisedDarkSoft: Qt.rgba(0, 0, 0, 0.52)
    readonly property color raisedLight: Qt.rgba(0.294, 0.294, 0.294, 0.11)
    readonly property color raisedLightSoft: Qt.rgba(0.294, 0.294, 0.294, 0.09)
    readonly property color insetDark: Qt.rgba(0, 0, 0, 0.60)
    readonly property color insetLight: Qt.rgba(0.294, 0.294, 0.294, 0.09)

    // Accent remains visible as a state cue, but never becomes an opaque halo.
    readonly property color accentBorder: Qt.rgba(1, 0.4, 0, 0.24)
    readonly property color accentGlow: Qt.rgba(1, 0.4, 0, 0.075)
    readonly property color accentGlowSoft: Qt.rgba(1, 0.4, 0, 0.035)
    readonly property color accentGlowStrong: Qt.rgba(1, 0.4, 0, 0.10)
    readonly property color accentLine: Qt.rgba(1, 0.4, 0, 0.16)

    readonly property int radiusXL: 28
    readonly property int radiusLG: 22
    readonly property int radiusMD: 16
    readonly property int radiusSM: 12
}
