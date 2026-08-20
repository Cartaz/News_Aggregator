"""Regression tests for the deep Dark Neumorphism presentation architecture."""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("PySide6")
pytestmark = pytest.mark.ui


def test_generic_qwidget_is_not_forced_opaque() -> None:
    from ui.styles.neumorphism import build_global_qss

    qss = build_global_qss()
    generic = qss.split("QWidget {", 1)[1].split("}", 1)[0]
    assert "background-color" not in generic


def test_main_panels_are_material_surfaces(qtbot) -> None:  # type: ignore[no-untyped-def]
    from ui.widgets.news_view import NewsView
    from ui.widgets.neumorphic_surfaces import NeumorphicPanel
    from ui.widgets.source_list import SourceList

    source = SourceList()
    news = NewsView()
    qtbot.addWidget(source)
    qtbot.addWidget(news)
    assert isinstance(source, NeumorphicPanel)
    assert isinstance(news, NeumorphicPanel)


def test_scroll_views_use_direct_viewport_painting(qtbot) -> None:  # type: ignore[no-untyped-def]
    from ui.widgets.neumorphic_surfaces import (
        NeumorphicTableWidget,
        NeumorphicTextBrowser,
        NeumorphicTreeWidget,
    )

    widgets = [
        NeumorphicTreeWidget(),
        NeumorphicTableWidget(0, 4),
        NeumorphicTextBrowser(),
    ]
    for widget in widgets:
        qtbot.addWidget(widget)
        source = inspect.getsource(type(widget).paintEvent)
        assert "_paint_inset_rim" in source
        assert widget.property("neumorphicView") is True
        assert widget.viewport().property("neumorphicViewport") is True


def test_viewport_rim_painter_targets_viewport() -> None:
    from ui.widgets.neumorphic_surfaces import _paint_inset_rim

    source = inspect.getsource(_paint_inset_rim)
    assert "QPainter(viewport)" in source
    assert "draw_inset_edge_overlay" in source


def test_line_edit_uses_three_pass_painting() -> None:
    from ui.widgets.neumorphic_controls import NeumorphicLineEdit

    source = inspect.getsource(NeumorphicLineEdit.paintEvent)
    first_material = source.find("draw_inset_surface")
    native = source.find("super().paintEvent")
    top_rim = source.find("draw_inset_edge_overlay")
    assert -1 not in (first_material, native, top_rim)
    assert first_material < native < top_rim


def test_panel_overlay_is_mouse_transparent(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtCore import Qt

    from ui.widgets.neumorphic_surfaces import NeumorphicPanel

    panel = NeumorphicPanel()
    qtbot.addWidget(panel)
    overlay = panel._surface_overlay
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
