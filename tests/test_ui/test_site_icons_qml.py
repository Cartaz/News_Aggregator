"""Static contracts for application and source icon presentation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "ui" / "qml"


def test_accent_icon_component_colorizes_without_extra_shadow() -> None:
    source = (QML / "AccentIcon.qml").read_text(encoding="utf-8")
    assert "import QtQuick.Effects" in source
    assert "MultiEffect" in source
    assert "saturation: -1.0" in source
    assert "colorization: 1.0" in source
    assert "colorizationColor: root.tint" in source
    assert "shadowEnabled" not in source


def test_program_mark_is_used_in_header_and_all_articles_row() -> None:
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    row = (QML / "SourceRow.qml").read_text(encoding="utf-8")
    icon_path = '../../assets/icons/news-aggregator.svg'
    assert "AccentIcon" in main
    assert icon_path in main
    assert 'root.kind === "all"' in row
    assert icon_path in row


def test_source_rows_accept_cached_site_icons_and_keep_category_symbol() -> None:
    row = (QML / "SourceRow.qml").read_text(encoding="utf-8")
    models = (ROOT / "ui" / "models.py").read_text(encoding="utf-8")
    assert "required property string iconSource" in row
    assert 'root.kind === "category" ? "◇"' in row
    assert 'root.kind === "feed" && root.iconSource.length > 0' in row
    assert 'b"iconSource"' in models


def test_article_columns_do_not_size_children_from_the_layout_itself() -> None:
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    assert "articleColumns.width *" not in main
    assert "contentArea.width *" in main
