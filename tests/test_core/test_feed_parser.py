"""Test per core/feed_parser.py."""

from __future__ import annotations

import pytest

from core.exceptions import FeedParseError
from core.feed_parser import parse_feed_bytes, strip_html, truncate


def test_strip_html_simple() -> None:
    """strip_html deve rimuovere i tag base."""
    assert strip_html("<p>ciao</p>") == "ciao"
    assert strip_html("<b>bold</b>") == "bold"


def test_strip_html_with_entities() -> None:
    """strip_html deve preservare le entity HTML come testo."""
    text: str = strip_html("<p>Testo &amp; altro</p>")
    assert "Testo" in text and "altro" in text


def test_strip_html_empty() -> None:
    """strip_html deve restituire stringa vuota per input vuoto."""
    assert strip_html("") == ""
    assert strip_html(None) == ""  # type: ignore[arg-type]


def test_strip_html_nested() -> None:
    """strip_html deve gestire tag annidati."""
    text: str = strip_html("<div><p>uno</p><p>due</p></div>")
    assert "uno" in text and "due" in text


def test_truncate_short() -> None:
    """truncate non deve modificare testi sotto il limite."""
    assert truncate("ciao", 10) == "ciao"


def test_truncate_long() -> None:
    """truncate deve tagliare e aggiungere ellissi."""
    text: str = truncate("abcdefghijklmnopqrstuvwxyz", 10)
    assert len(text) == 10
    assert text.endswith("\u2026")


def test_parse_valid_rss(sample_rss_bytes: bytes) -> None:
    """Il parser deve estrarre titolo e 2 articoli dal feed di esempio."""
    title, items = parse_feed_bytes(sample_rss_bytes, "src1", "https://x")
    assert title == "Feed di Prova"
    assert len(items) == 2
    assert items[0].title == "Primo articolo"
    assert items[0].link == "https://example.com/1"
    assert "HTML" in items[0].summary
    assert "<" not in items[0].summary


def test_parse_empty_content() -> None:
    """Contenuto vuoto deve sollevare FeedParseError."""
    with pytest.raises(FeedParseError):
        parse_feed_bytes(b"", "src1", "https://x")


def test_parse_invalid_xml() -> None:
    """XML non valido senza entries deve sollevare FeedParseError."""
    with pytest.raises(FeedParseError):
        parse_feed_bytes(b"not xml at all", "src1", "https://x")


def test_parse_preserves_source_id(sample_rss_bytes: bytes) -> None:
    """Il source_id passato deve essere propagato agli articoli."""
    _, items = parse_feed_bytes(sample_rss_bytes, "my_src", "https://x")
    for item in items:
        assert item.source_id == "my_src"


def test_parse_item_has_stable_id(sample_rss_bytes: bytes) -> None:
    """Gli articoli devono avere ID stabili derivati dal link."""
    _, items = parse_feed_bytes(sample_rss_bytes, "src", "https://x")
    assert all(len(it.id) > 0 for it in items)
    assert items[0].id != items[1].id
