"""Minimal stand-ins for streamed HTTP responses used by the feed transport."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

import requests


class FakeResponse:
    """Enough of ``requests.Response``/``curl_cffi`` responses for streaming reads."""

    def __init__(
        self,
        content: bytes = b"",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        url: str = "",
        chunk_size: int = 64 * 1024,
    ) -> None:
        self.content = content
        self.status_code = status_code
        self.headers = dict(headers or {})
        self.url = url
        self.encoding = "utf-8"
        self._chunk_size = chunk_size
        self.closed = False

    def iter_content(self, chunk_size: int | None = None) -> Iterator[bytes]:
        size = chunk_size or self._chunk_size
        for start in range(0, len(self.content), size):
            yield self.content[start:start + size]

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class FakeCurlRequests:
    """Fake ``curl_cffi.requests`` module recording every GET."""

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def Session(self) -> FakeCurlRequests:  # noqa: N802 - mirrors curl_cffi API
        return self

    def __enter__(self) -> FakeCurlRequests:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def get(self, url: str, **_kwargs: object) -> FakeResponse:
        self.calls.append(url)
        outcome = self._responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
