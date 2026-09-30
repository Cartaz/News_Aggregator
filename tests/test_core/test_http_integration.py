"""Exercise real HTTP discovery, conditional refresh and persistent read state."""

import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.feed_manager import FeedManager


def test_real_http_discovery_recovers_second_feed_and_handles_304(tmp_paths, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    requests_seen = []
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    feed = f'<rss version="2.0"><channel><title>Real HTTP</title><item><title>News</title><guid>urn:one</guid><pubDate>{date}</pubDate></item></channel></rss>'.encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests_seen.append((self.path, self.headers.get("If-None-Match")))
            if self.path == "/":
                body = b'<html><head><link rel="alternate" type="application/rss+xml" href="/broken.xml"><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head></html>'
            elif self.path == "/broken.xml":
                body = b'<html>Not a feed</html>'
            elif self.headers.get("If-None-Match") == '"one"':
                self.send_response(304)
                self.end_headers()
                return
            else:
                body = feed
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            if self.path == "/feed.xml":
                self.send_header("ETag", '"one"')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        manager = FeedManager()
        source = manager.add(f"http://127.0.0.1:{server.server_port}/")
        assert manager.refresh(source.id) == 1
        saved = manager.get(source.id)
        manager.mark_read(source.id, saved.items[0].id)
        assert manager.refresh(source.id) == 0
        restored = FeedManager().get(source.id)
        assert restored.items[0].read
        assert restored.resolved_feed_url.endswith("/feed.xml")
        assert requests_seen == [("/", None), ("/broken.xml", None), ("/feed.xml", None), ("/feed.xml", '"one"')]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
