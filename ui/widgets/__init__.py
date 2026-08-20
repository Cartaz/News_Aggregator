"""Pacchetto widgets: componenti UI riutilizzabili per Neumorphism."""

from __future__ import annotations

from ui.widgets.action_button import ActionButton
from ui.widgets.card import Card
from ui.widgets.feed_input import FeedInput, is_valid_url, normalize_url
from ui.widgets.news_view import NewsView
from ui.widgets.news_view_table import format_date, format_time, populate_table
from ui.widgets.shortcut_badge import ShortcutBadge
from ui.widgets.source_list import SourceList
from ui.widgets.source_list_menu import show_context_menu
from ui.widgets.source_tree_builder import build_tree
from ui.widgets.status_indicator import StatusIndicator

__all__ = [
    "ActionButton",
    "Card",
    "FeedInput",
    "is_valid_url",
    "normalize_url",
    "NewsView",
    "format_date",
    "format_time",
    "populate_table",
    "ShortcutBadge",
    "SourceList",
    "show_context_menu",
    "build_tree",
    "StatusIndicator",
]
