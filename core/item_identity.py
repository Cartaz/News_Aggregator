"""Identità stabile e normalizzazione URL per gli articoli."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "utm_campaign",
    "utm_content",
    "utm_id",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def canonicalize_url(raw_url: str) -> str:
    """Normalizza un URL senza alterarne la parte semanticamente utile.

    Rimuove fragment e parametri di tracking noti, normalizza schema/host e
    conserva path, query non-tracking e relativo ordine.
    """
    value = (raw_url or "").strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return value
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    netloc = f"{userinfo}{hostname}"
    if port is not None:
        netloc += f":{port}"

    query_pairs = [
        (key, item_value)
        for key, item_value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_KEYS
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, parsed.path, query, ""))


def fallback_identity_key(title: str, published: datetime) -> str:
    """Chiave leggibile/stabile usata quando GUID e URL non bastano."""
    normalized_title = " ".join((title or "").casefold().split())
    aware = published
    if aware.tzinfo is None:
        aware = aware.replace(tzinfo=timezone.utc)
    timestamp = aware.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    return f"{normalized_title}|{timestamp}"


def make_item_id(
    source_id: str,
    title: str,
    link: str,
    published: datetime,
    guid: str = "",
) -> str:
    """Genera l'ID articolo secondo GUID → URL canonico → fallback."""
    clean_guid = (guid or "").strip()
    canonical_link = canonicalize_url(link)
    if clean_guid:
        identity = f"guid:{source_id}:{clean_guid}"
    elif canonical_link:
        identity = f"url:{source_id}:{canonical_link}"
    else:
        identity = f"fallback:{source_id}:{fallback_identity_key(title, published)}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]


def legacy_link_id(link: str) -> str:
    """ID usato dalle versioni precedenti: SHA1 del link grezzo."""
    return hashlib.sha1((link or "").encode("utf-8")).hexdigest()[:16]


__all__ = [
    "canonicalize_url",
    "fallback_identity_key",
    "legacy_link_id",
    "make_item_id",
]
