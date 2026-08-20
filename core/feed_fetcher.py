"""Recupero feed via HTTP, auto-discovery e parsing del contenuto.

Usa ``fetch_url`` (con fallback ``curl_cffi``) per il download, e
``feed_link_extractor`` per l'auto-discovery dei feed RSS/Atom da
pagine HTML. Framework-agnostic: solleva ``FeedError``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from config.constants import FeedDefaults
from core.exceptions import FeedFetchError, FeedParseError
from core.feed_http import fetch_url, fetch_url_simple
from core.feed_link_extractor import extract_feed_links
from core.feed_parser import parse_feed_bytes
from core.models import FeedItem

logger = logging.getLogger(__name__)

_XML_SNIFF_PREFIX: bytes = b"<?xml"
_XML_ROOT_TAGS: tuple[bytes, ...] = (b"<rss", b"<feed", b"<rdf:RDF")


# Siti la cui homepage è protetta da WAF/Cloudflare ma che offrono feed
# RSS pubblici su URL non-standard (subdominio diverso o path non-standard).
# Quando l'auto-discovery standard fallisce, proviamo questi URL noti.
# Aggiungere qui solo siti molto diffusi per i quali l'UX di inserire
# la homepage e ottenere automaticamente il feed vale il costo di
# manutenzione della lista.
_KNOWN_FEED_OVERRIDES: dict[str, list[str]] = {
    # Bloomberg: homepage www.bloomberg.com bloccata da Cloudflare WAF
    # aggressivo (anche curl_cffi non passa). I feed reali vivono su un
    # sottodominio diverso (feeds.bloomberg.com) che non ha WAF.
    # Le sezioni regionali (europe, asia, africa, americas, middle-east)
    # NON hanno feed dedicato — usiamo il feed generico /news.rss come
    # fallback per tutte, incluso /europe.
    "www.bloomberg.com": [
        "https://feeds.bloomberg.com/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.bloomberg.com/politics/news.rss",
        "https://feeds.bloomberg.com/economics/news.rss",
        "https://feeds.bloomberg.com/business/news.rss",
    ],
    # The Economist: homepage bloccata da WAF e nessun <link rel=alternate>
    # nell'HTML. I feed reali sono su path per-sezione del tipo
    # /<sezione>/rss.xml. Includiamo le sezioni principali.
    "www.economist.com": [
        "https://www.economist.com/leaders/rss.xml",
        "https://www.economist.com/briefing/rss.xml",
        "https://www.economist.com/the-world-this-week/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.economist.com/science-and-technology/rss.xml",
        "https://www.economist.com/the-economist-explains/rss.xml",
    ],
}


def _looks_like_xml(content: bytes) -> bool:
    """Verifica se il contenuto appare essere XML (RSS/Atom)."""
    if not content:
        return False
    head: bytes = content[:500].lstrip()
    if head.startswith(_XML_SNIFF_PREFIX):
        return True
    return any(tag in head for tag in _XML_ROOT_TAGS)


def _looks_like_html(content: bytes) -> bool:
    """Verifica se il contenuto appare essere HTML."""
    if not content:
        return False
    head: bytes = content[:500].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _is_feed_url(url: str) -> bool:
    """Verifica se l'URL ha un'estensione che suggerisce un feed."""
    path: str = urlparse(url).path.lower()
    return any(
        path.endswith(ext)
        for ext in (".xml", ".rss", ".atom", "/feed", "/rss", "/feed/")
    )


def fetch_and_parse(
    url: str, source_id: str, timeout: int | None = None
) -> tuple[str, list[FeedItem]]:
    """Recupera via HTTP un feed e lo analizza, con auto-discovery.

    Logica:
    1. Scarica l'URL con ``fetch_url`` (fallback curl_cffi per WAF).
       Se il fetch fallisce con errore di rete (403, 404, timeout),
       passa direttamente al passo 4 (fallback paths): alcuni siti
       (Bloomberg, The Economist) hanno homepage bloccate da WAF
       ma feed accessibili su URL alternativi noti.
    2. Se il contenuto è XML valido, parsalo direttamente.
    3. Se il contenuto è HTML, cerca ``<link rel="alternate">`` per
       trovare il feed reale e scarica quello.
    4. Se nessuna delle due, prova i path fallback da
       ``_guess_feed_paths`` (path standard + override per siti noti).
    """
    actual_timeout: int = timeout or FeedDefaults.REQUEST_TIMEOUT_SECONDS

    # Tentativo 1: scarica l'URL principale
    content: bytes = b""
    fetch_failed: bool = False
    try:
        content = fetch_url(url, actual_timeout)
    except FeedFetchError as exc:
        # L'URL principale non è raggiungibile (WAF, 404, timeout).
        # NON ci arrendiamo subito: proviamo i path fallback, perché
        # alcuni siti (Bloomberg, Economist) hanno homepage bloccate
        # ma feed accessibili su URL alternativi.
        logger.debug(
            "Fetch iniziale fallito per %s, provo path fallback: %s",
            url, exc,
        )
        fetch_failed = True

    if not fetch_failed:
        if not content:
            raise FeedFetchError(url, "risposta vuota")

        final_url: str = url

        # Caso 1: il contenuto è già un feed XML
        if _looks_like_xml(content):
            logger.debug("Contenuto rilevato come XML, parsing diretto")
            return parse_feed_bytes(content, source_id, final_url)

        # Caso 2: HTML con auto-discovery
        if _looks_like_html(content) or not _looks_like_xml(content):
            feed_urls: list[str] = extract_feed_links(content, final_url)
            if feed_urls:
                logger.info(
                    "Auto-discovery: trovati %d feed in %s, provo %s",
                    len(feed_urls), final_url, feed_urls[0],
                )
                return _fetch_feed_recursive(
                    feed_urls[0], source_id, actual_timeout
                )
            # Fallback: prova path comuni se l'URL originale non li aveva
            if not _is_feed_url(final_url):
                candidates: list[str] = _guess_feed_paths(final_url)
                for candidate in candidates:
                    logger.info(
                        "Auto-discovery fallback: provo path %s", candidate
                    )
                    try:
                        result = _fetch_feed_recursive(
                            candidate, source_id, actual_timeout
                        )
                        logger.info(
                            "Auto-discovery: feed trovato a %s", candidate
                        )
                        return result
                    except (FeedFetchError, FeedParseError) as exc:
                        logger.debug(
                            "Fallback path %s fallito: %s", candidate, exc
                        )
                        continue

        raise FeedParseError(
            final_url,
            "contenuto non è un feed RSS/Atom né una pagina HTML con link "
            "a un feed. Verifica che l'URL sia corretto.",
        )

    # Caso 3: fetch iniziale fallito — prova SOLO i path fallback.
    # (niente auto-discovery da HTML perché non abbiamo HTML)
    if not _is_feed_url(url):
        candidates = _guess_feed_paths(url)
        last_exc: FeedFetchError | FeedParseError | None = None
        for candidate in candidates:
            logger.info(
                "Auto-discovery fallback (fetch fallito): provo %s", candidate
            )
            try:
                result = _fetch_feed_recursive(
                    candidate, source_id, actual_timeout
                )
                logger.info("Auto-discovery: feed trovato a %s", candidate)
                return result
            except (FeedFetchError, FeedParseError) as exc:
                logger.debug("Fallback path %s fallito: %s", candidate, exc)
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc

    # Nessun fallback disponibile: rilancia un errore chiaro
    raise FeedFetchError(
        url,
        "URL principale non raggiungibile e nessun path fallback "
        "disponibile. Verifica l'URL o inseriscine uno diretto al feed.",
    )


def _fetch_feed_recursive(
    url: str, source_id: str, timeout: int
) -> tuple[str, list[FeedItem]]:
    """Scarica e analizza un URL di feed noto (con fallback curl_cffi).

    A differenza di ``fetch_and_parse``, questa funzione viene chiamata
    solo su URL che si presume essere feed (da auto-discovery o path
    fallback). Esegue comunque un sanity check sul contenuto: se il
    server risponde con HTML (es. Cloudflare challenge page, errore
    renderizzato, o homepage invece di RSS), solleviamo subito
    ``FeedParseError`` con un messaggio chiaro invece di passare
    byte non-XML a ``feedparser`` che genererebbe un errore generico
    "not well-formed (invalid token)".
    """
    content: bytes = fetch_url(url, timeout)
    if not content:
        raise FeedFetchError(url, "risposta vuota")
    # Sanity check: se la risposta è HTML, non è un feed.
    # Il server potrebbe aver servito una homepage, una pagina di
    # errore renderizzata, o la challenge page di Cloudflare.
    if _looks_like_html(content):
        raise FeedParseError(
            url,
            "il server ha risposto con HTML, non con un feed RSS/Atom. "
            "Possibile causa: WAF/bot-detection che serve una challenge "
            "page, oppure l'URL non punta a un feed reale.",
        )
    # Se non è chiaramente XML ma nemmeno HTML, proviamo comunque a
    # parsarlo: feedparser è tollerante. Se il contenuto è brotli non
    # decompresso, l'errore arriverà qui ma con un messaggio che
    # l'utente può comprendere grazie al warning in feed_http.py.
    return parse_feed_bytes(content, source_id, url)


def _guess_feed_paths(base_url: str) -> list[str]:
    """Genera una lista di URL di feed plausibili da un URL base.

    Include i path standard più comuni:
    - /rss.xml, /feed/, /feed.xml, /rss, /atom.xml, /index.xml
      (WordPress, Ghost, Hugo, Jekyll, feedburner-like)
    - /feeds.xml (Future plc network: tomshardware.com, techradar.com,
      gamesradar.com, pcgamer.com — tutti usano /feeds.xml)

    Per siti noti con homepage bloccata da WAF ma feed pubblici
    accessibili (Bloomberg, The Economist), include anche gli URL
    di feed noti dalla tabella ``_KNOWN_FEED_OVERRIDES``.

    NON include /rss/news e /rss/reviews: sono path non standard
    che generano solo rumore nei log (hoardware.it li serve come
    HTML, non come feed, generando falsi positivi di "200 OK" che
    poi falliscono al parsing).
    """
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    # Path standard (solo per URL root)
    standard_paths: list[str] = []
    if not parsed.path or parsed.path == "/" or parsed.path == "":
        base = f"{parsed.scheme}://{parsed.netloc}"
        standard_paths = [
            f"{base}/rss.xml",
            f"{base}/feed/",
            f"{base}/feed.xml",
            f"{base}/feeds.xml",
            f"{base}/rss",
            f"{base}/atom.xml",
            f"{base}/index.xml",
        ]

    # Per siti noti con WAF aggressivo, includiamo gli URL di feed
    # noti anche quando l'URL ha un path (es. bloomberg.com/europe).
    # Questo perché alcune sezioni (es. /europe, /asia) NON hanno un
    # feed dedicato e l'utente si aspetta di poter aggiungere la
    # sezione e ottenere comunque un feed della testata.
    overrides: list[str] = _KNOWN_FEED_OVERRIDES.get(parsed.netloc.lower(), [])

    return standard_paths + overrides


__all__ = ["fetch_and_parse"]
