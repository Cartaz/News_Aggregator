"""Framework-agnostic application core public surface."""

from __future__ import annotations

from core.app_controller import AppController
from core.exceptions import (
    AppError,
    ConfigError,
    ConfigValidationError,
    FeedDuplicateError,
    FeedError,
    FeedFetchError,
    FeedNotFoundError,
    FeedParseError,
    UIError,
)
from core.feed_fetcher import fetch_and_parse
from core.feed_manager import FeedManager
from core.feed_parser import parse_feed_bytes, strip_html, truncate
from core.feed_serializer import deserialize_source, serialize_source
from core.models import FeedCategory, FeedItem, FeedSource

__all__ = [
    "AppController",
    "AppError",
    "ConfigError",
    "ConfigValidationError",
    "FeedError",
    "FeedFetchError",
    "FeedNotFoundError",
    "FeedDuplicateError",
    "FeedParseError",
    "UIError",
    "FeedManager",
    "FeedItem",
    "FeedSource",
    "FeedCategory",
    "fetch_and_parse",
    "parse_feed_bytes",
    "strip_html",
    "truncate",
    "deserialize_source",
    "serialize_source",
]
