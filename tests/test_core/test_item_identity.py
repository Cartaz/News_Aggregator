"""Regression tests for robust article identity and deduplication."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from core.feed_parser import parse_feed_bytes
from core.feed_serializer import deserialize_source, serialize_source
from core.item_identity import canonicalize_url
from core.models import FeedItem, FeedSource

NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)


def _item(*, link: str, guid: str = "", title: str = "Article") -> FeedItem:
    return FeedItem.from_raw(
        source_id="source-1",
        title=title,
        link=link,
        summary="",
        published=NOW,
        guid=guid,
    )


def test_guid_has_priority_over_changed_link() -> None:
    first = _item(link="https://example.com/old", guid="post-42")
    second = _item(link="https://example.com/new", guid="post-42")
    assert first.id == second.id
    assert first.guid == "post-42"


def test_tracking_parameters_do_not_change_identity() -> None:
    tracked = _item(
        link="https://Example.com/story?id=9&utm_source=rss&utm_campaign=test#top"
    )
    clean = _item(link="https://example.com/story?id=9")
    assert tracked.id == clean.id
    assert tracked.link == "https://example.com/story?id=9"


def test_canonicalize_url_preserves_non_tracking_query_order() -> None:
    assert canonicalize_url(
        "HTTPS://Example.COM:443/a?b=2&utm_medium=rss&a=1#fragment"
    ) == "https://example.com/a?b=2&a=1"


def test_fallback_identity_works_without_link_or_guid() -> None:
    first = _item(link="", title="Same title")
    second = _item(link="", title="  same   TITLE  ")
    assert first.id == second.id
    assert first.link == ""


def test_legacy_link_id_migrates_without_becoming_new() -> None:
    old_link = "https://example.com/story?utm_source=rss&id=7"
    old = FeedItem(
        id=hashlib.sha1(old_link.encode("utf-8")).hexdigest()[:16],
        source_id="source-1",
        title="Article",
        link=old_link,
        summary="old",
        published=NOW,
        read=True,
    )
    source = FeedSource("https://example.com/feed.xml", items=[old])
    new = _item(link="https://example.com/story?id=7", guid="guid-7")

    brand_new = source.replace_items([new])

    assert brand_new == []
    assert len(source.items) == 1
    assert source.items[0].id == new.id
    assert source.items[0].guid == "guid-7"
    assert source.items[0].read is True


def test_same_guid_with_changed_link_is_not_new_after_migration() -> None:
    source = FeedSource("https://example.com/feed.xml")
    first = _item(link="https://example.com/a", guid="stable-guid")
    second = _item(link="https://example.com/b", guid="stable-guid")

    assert source.replace_items([first]) == [first]
    source.mark_read(first.id)
    assert source.replace_items([second]) == []
    assert source.items[0].read is True
    assert source.items[0].link == "https://example.com/b"


def test_guid_persists_and_old_json_without_guid_is_compatible() -> None:
    item = _item(link="https://example.com/a", guid="guid-a")
    source = FeedSource("https://example.com/feed.xml", items=[item])
    encoded = serialize_source(source)
    assert encoded["items"][0]["guid"] == "guid-a"

    encoded["items"][0].pop("guid")
    decoded = deserialize_source(encoded)
    assert decoded.items[0].guid == ""


def test_parser_deduplicates_duplicate_guid_entries() -> None:
    xml = b"""<?xml version='1.0'?>
<rss version='2.0'><channel><title>Example</title>
<item><title>One</title><link>https://example.com/one</link><guid>same</guid>
<pubDate>Fri, 21 Aug 2026 10:00:00 +0000</pubDate></item>
<item><title>Duplicate</title><link>https://example.com/two</link><guid>same</guid>
<pubDate>Fri, 21 Aug 2026 10:01:00 +0000</pubDate></item>
</channel></rss>"""
    _, items = parse_feed_bytes(xml, "source-1", "https://example.com/feed.xml")
    assert len(items) == 1
    assert items[0].guid == "same"


def test_parser_accepts_linkless_item_with_guid() -> None:
    xml = b"""<?xml version='1.0'?>
<rss version='2.0'><channel><title>Example</title>
<item><title>One</title><guid isPermaLink='false'>opaque-1</guid>
<pubDate>Fri, 21 Aug 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""
    _, items = parse_feed_bytes(xml, "source-1", "https://example.com/feed.xml")
    assert len(items) == 1
    assert items[0].guid == "opaque-1"
    assert items[0].link == ""
