"""Static regression contracts for the Qt Quick/QML presentation layer."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QML_ROOT = PROJECT_ROOT / "ui" / "qml"
MAIN_QML = QML_ROOT / "Main.qml"
APP_DIALOGS = QML_ROOT / "AppDialogs.qml"
THEME_QML = QML_ROOT / "Theme.qml"
WINDOW_PY = PROJECT_ROOT / "ui" / "window.py"
CONTROLLER_PY = PROJECT_ROOT / "ui" / "controller.py"
MODELS_PY = PROJECT_ROOT / "ui" / "models.py"
PREFERENCES_PY = PROJECT_ROOT / "ui" / "preferences.py"
DIAGNOSTICS_PY = PROJECT_ROOT / "ui" / "diagnostics.py"
INSTALLER = PROJECT_ROOT / "install.sh"


def test_required_qml_assets_exist() -> None:
    for name in (
        "Main.qml",
        "Theme.qml",
        "RaisedSurface.qml",
        "InsetSurface.qml",
        "NeuButton.qml",
        "NeuToggle.qml",
        "NeuTextField.qml",
        "SourceRow.qml",
        "ArticleRow.qml",
        "ModalSurface.qml",
        "Toast.qml",
        "AppDialogs.qml",
        "qmldir",
    ):
        assert (QML_ROOT / name).is_file()
    assert (QML_ROOT / "shaders" / "neumorphic_inset.frag").is_file()


def test_theme_tokens_match_dark_neumorphism_contract() -> None:
    source = THEME_QML.read_text(encoding="utf-8")
    assert 'surface: "#141414"' in source
    assert 'accent: "#ff6600"' in source
    assert 'textPrimary: "#e1e1e1"' in source
    assert 'textSecondary: "#878787"' in source
    assert 'textMuted: "#5a5a5a"' in source
    assert "radiusXL: 28" in source
    assert "radiusLG: 22" in source
    assert "radiusMD: 16" in source
    assert "radiusSM: 12" in source


def test_typography_scales_with_window_and_uses_cantarell() -> None:
    theme = THEME_QML.read_text(encoding="utf-8")
    main = MAIN_QML.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    assert 'availableFontFamilies.indexOf("Cantarell")' in theme
    assert '"Cantarell"' in theme
    assert "fontChoices" not in theme
    assert "userFontFamily" not in theme
    assert "property real userFontScale" in theme
    assert "property real viewportTextScale" in theme
    assert "userFontScale * viewportTextScale" in theme
    assert "function updateResponsiveTypography()" in main
    assert "onWidthChanged: updateResponsiveTypography()" in main
    assert "Theme.userFontScale = backend.preferences.fontScaleFactor" in main
    assert "cantarell-fonts" in installer
    assert "fonts-cantarell" in installer


def test_settings_no_longer_expose_font_picker() -> None:
    dialogs = APP_DIALOGS.read_text(encoding="utf-8")
    preferences = PREFERENCES_PY.read_text(encoding="utf-8")
    assert "Carattere UI" not in dialogs
    assert "fontGrid" not in dialogs
    assert "fontChoices" not in dialogs
    assert "settingsFont" not in dialogs
    assert "def fontFamily" not in preferences
    assert "font_family" not in preferences


def test_accent_glow_is_centralized_and_translucent() -> None:
    theme = THEME_QML.read_text(encoding="utf-8")
    raised = (QML_ROOT / "RaisedSurface.qml").read_text(encoding="utf-8")
    inset = (QML_ROOT / "InsetSurface.qml").read_text(encoding="utf-8")
    button = (QML_ROOT / "NeuButton.qml").read_text(encoding="utf-8")
    assert "accentBorder: Qt.rgba(1, 0.4, 0, 0.24)" in theme
    assert "accentGlow: Qt.rgba(1, 0.4, 0, 0.075)" in theme
    assert "accentGlowSoft: Qt.rgba(1, 0.4, 0, 0.035)" in theme
    assert "color: Theme.accentGlow" in raised
    assert "color: Theme.accentGlowSoft" in raised
    assert "color: Theme.accentGlow" in inset
    assert "color: Theme.accentGlowSoft" in inset
    assert "selected: root.accent && !tap.pressed" in button


def test_main_lists_are_virtualized_and_reuse_delegates() -> None:
    source = MAIN_QML.read_text(encoding="utf-8")
    assert "model: backend.sources" in source
    assert "model: backend.articles" in source
    assert source.count("reuseItems: true") >= 2
    assert "cacheBuffer: 0" in source


def test_selected_article_uses_one_shared_inset_highlight() -> None:
    source = MAIN_QML.read_text(encoding="utf-8")
    article_delegate = (QML_ROOT / "ArticleRow.qml").read_text(encoding="utf-8")
    assert "highlight: Item" in source
    assert "selected: true" in source
    assert "InsetSurface" in source
    assert "ShaderEffect" not in article_delegate


def test_responsive_workspace_has_named_panels_and_compact_widths() -> None:
    source = MAIN_QML.read_text(encoding="utf-8")
    assert "readonly property bool compactLayout" in source
    assert "readonly property bool denseLayout" in source
    assert 'objectName: "workspace"' in source
    assert 'objectName: "contentArea"' in source
    assert 'objectName: "articleColumns"' in source
    assert 'objectName: "articleListPanel"' in source
    assert 'objectName: "detailPanel"' in source
    assert "Layout.minimumWidth: root.denseLayout ? 270" in source
    assert "Layout.minimumWidth: root.denseLayout ? 300" in source


def test_shader_is_precompiled_with_multibackend_qsb() -> None:
    source = INSTALLER.read_text(encoding="utf-8")
    assert '"${QSB}" --qt6 -o "${SHADER_PACKAGE}" "${SHADER_SOURCE}"' in source
    assert 'grep -q "GLSL"' in source
    assert "neumorphic_inset.frag.qsb" in WINDOW_PY.read_text(encoding="utf-8")


def test_python_qml_boundary_is_typed_and_signal_driven() -> None:
    controller = CONTROLLER_PY.read_text(encoding="utf-8")
    models = MODELS_PY.read_text(encoding="utf-8")
    main_qml = MAIN_QML.read_text(encoding="utf-8")
    assert "QAbstractListModel" in models
    assert "@Slot(" in controller
    assert "Signal(" in controller
    assert "PreferencesAdapter" in controller
    assert "DiagnosticsAdapter" in controller
    assert "Connections {" in main_qml
    assert "setInterval" not in main_qml


def test_web_frontend_is_not_part_of_the_qml_runtime() -> None:
    assert not (PROJECT_ROOT / "ui" / "web").exists()
    assert not (PROJECT_ROOT / "ui" / "bridge.py").exists()
    source = WINDOW_PY.read_text(encoding="utf-8")
    assert "QQmlApplicationEngine" in source
    assert "QQuickWindow" in source
    assert "QWebEngineView" not in source
    assert "QWebChannel" not in source


def test_custom_interactive_components_expose_accessibility_metadata() -> None:
    for name in ("NeuButton.qml", "NeuToggle.qml", "NeuTextField.qml", "SourceRow.qml", "ArticleRow.qml"):
        source = (QML_ROOT / name).read_text(encoding="utf-8")
        assert "Accessible.role:" in source
        assert "Accessible.name:" in source
    assert "Accessible.onPressAction:" in (QML_ROOT / "NeuButton.qml").read_text(encoding="utf-8")
    assert "Accessible.checked:" in (QML_ROOT / "NeuToggle.qml").read_text(encoding="utf-8")


def test_sidebar_drag_uses_drag_start_width_instead_of_accumulating_translation() -> None:
    source = MAIN_QML.read_text(encoding="utf-8")
    assert "property real sidebarDragStartWidth" in source
    assert "root.sidebarDragStartWidth + translation.x" in source
    assert "root.sidebarWidth + translation.x" not in source


def test_preferences_and_diagnostics_are_focused_adapters() -> None:
    preferences = PREFERENCES_PY.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS_PY.read_text(encoding="utf-8")
    assert "class PreferencesAdapter(QObject)" in preferences
    assert "update_settings_async" in preferences
    assert "get_log_tail" not in preferences
    assert "class DiagnosticsAdapter(QObject)" in diagnostics
    assert "get_log_tail" in diagnostics
    assert "update_settings" not in diagnostics


def test_custom_toggle_has_specific_accessible_label_per_use() -> None:
    toggle = (QML_ROOT / "NeuToggle.qml").read_text(encoding="utf-8")
    main = MAIN_QML.read_text(encoding="utf-8")
    assert 'property string accessibleName: "Interruttore"' in toggle
    assert "Accessible.name: root.accessibleName" in toggle
    assert "Accessible.onToggleAction: root.toggle()" in toggle
    dialogs = APP_DIALOGS.read_text(encoding="utf-8")
    assert 'accessibleName: "Solo non letti"' in main
    assert 'accessibleName: "Segna letto quando cambi articolo"' in dialogs
    assert 'accessibleName: "Notifiche desktop per nuovi articoli"' in dialogs
    assert 'accessibleName: "Chiudi la finestra nel tray"' in dialogs


def test_search_field_is_accessible_and_only_sends_user_edits() -> None:
    main = MAIN_QML.read_text(encoding="utf-8")
    assert 'Accessible.name: "Cerca negli articoli"' in main
    assert "Accessible.searchEdit: true" in main
    assert "onTextEdited: backend.setSearchQuery(text)" in main
    assert "onTextChanged: backend.setSearchQuery(text)" not in main


def test_refresh_progress_is_segmented_per_feed() -> None:
    main = MAIN_QML.read_text(encoding="utf-8")
    assert "Repeater {" in main
    assert "model: backend.refreshTotal" in main
    assert "index < backend.refreshCurrent ? Theme.accent" in main
    assert "Accessible.role: Accessible.ProgressBar" in main


def test_modals_disable_underlay_and_restore_focus() -> None:
    main = MAIN_QML.read_text(encoding="utf-8")
    dialogs = APP_DIALOGS.read_text(encoding="utf-8")
    assert "enabled: !dialogs.opened" in main
    assert "property var modalReturnFocus" in dialogs
    assert "root.Window.window.activeFocusItem" in dialogs
    assert "target.forceActiveFocus()" in dialogs
    assert "function finishDialog()" in dialogs
