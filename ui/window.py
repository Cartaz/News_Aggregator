"""Native Qt Quick shell for the QML desktop interface."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, Paths, UIConstraints
from core.app_controller import AppController
from ui.controller import UiController

logger = logging.getLogger(__name__)


class QmlMainWindow(QObject):
    """Own QML engine/window lifecycle without absorbing application rules."""

    def __init__(
        self,
        controller: AppController,
        ui_controller: UiController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self.ui = ui_controller
        self._force_close = False

        qml_root = Path(__file__).resolve().parent / "qml"
        shader_package = qml_root / "shaders" / "neumorphic_inset.frag.qsb"
        if not shader_package.is_file():
            raise RuntimeError(
                "Shader QML non compilato. Esegui ./install.sh prima di avviare l'app."
            )

        self._engine = QQmlApplicationEngine(self)
        self._engine.rootContext().setContextProperty("backend", self.ui)
        self._engine.load(QUrl.fromLocalFile(str(qml_root / "Main.qml")))
        roots = self._engine.rootObjects()
        if not roots or not isinstance(roots[0], QQuickWindow):
            raise RuntimeError("Main.qml non ha creato una finestra Qt Quick valida")
        self._window: QQuickWindow = roots[0]
        self._window.setTitle(AppMeta.DISPLAY_NAME)
        self._window.setMinimumWidth(UIConstraints.WINDOW_MIN_WIDTH)
        self._window.setMinimumHeight(UIConstraints.WINDOW_MIN_HEIGHT)
        self._window.resize(
            controller.settings.window_width,
            controller.settings.window_height,
        )
        if Paths.APP_ICON.exists():
            self._window.setIcon(QIcon(str(Paths.APP_ICON)))

        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(350)
        self._geometry_timer.timeout.connect(self._persist_geometry)
        self._window.installEventFilter(self)

        self.ui.requestQuit.connect(self.force_quit)
        self.ui.requestHide.connect(self.hide_to_tray)

    @property
    def window(self) -> QQuickWindow:
        return self._window

    def show(self) -> None:
        self._window.show()

    def restore_from_tray(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.requestActivate()
        self.ui.sync()

    def hide_to_tray(self) -> None:
        self._persist_geometry()
        self._window.hide()

    def force_quit(self) -> None:
        self._force_close = True
        self._persist_geometry()
        QApplication.quit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if watched is not self._window:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Type.Resize:
            self._geometry_timer.start()
        elif event_type in {QEvent.Type.Show, QEvent.Type.WindowActivate}:
            self.ui.sync()
        elif event_type == QEvent.Type.Close:
            self._persist_geometry()
            if self._controller.settings.close_to_tray and not self._force_close:
                if isinstance(event, QCloseEvent):
                    event.ignore()
                self._window.hide()
                return True
            if isinstance(event, QCloseEvent):
                event.accept()
            QApplication.quit()
        return super().eventFilter(watched, event)

    def _persist_geometry(self) -> None:
        if not hasattr(self, "_window"):
            return
        # Collapse the resize debounce and any explicit close/hide save into one
        # persistence request for the latest geometry.
        self._geometry_timer.stop()
        operation_id = self._controller.persist_window_geometry_async(
            self._window.width(),
            self._window.height(),
        )
        if operation_id is None:
            logger.debug("Persistenza geometria non accettata durante shutdown")

    def shutdown(self) -> None:
        """Release UI observers before the controller is shut down."""
        self._geometry_timer.stop()
        self.ui.shutdown()


__all__ = ["QmlMainWindow"]
