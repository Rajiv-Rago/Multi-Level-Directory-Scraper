"""URL frontier with deduplication, normalization, and per-level queues."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication comparison."""
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.hostname.lower() if parsed.hostname else ""

    port = parsed.port
    if port and ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        port = None
    if port:
        netloc = f"{netloc}:{port}"

    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


@dataclass
class FrontierItem:
    url: str
    depth: int
    ancestors: list[dict] = field(default_factory=list)


class URLFrontier:
    """URL frontier with dedup, normalization, and per-level queues."""

    def __init__(self) -> None:
        self._visited: set[str] = set()
        self._queues: defaultdict[int, deque[FrontierItem]] = defaultdict(deque)

    def add(self, url: str, depth: int, ancestors: list[dict] | None = None) -> bool:
        normalized = normalize_url(url)
        if normalized in self._visited:
            return False
        self._visited.add(normalized)
        self._queues[depth].append(
            FrontierItem(url=normalized, depth=depth, ancestors=ancestors or [])
        )
        return True

    def pop(self, depth: int) -> FrontierItem | None:
        queue = self._queues.get(depth)
        if queue:
            return queue.popleft()
        return None

    def has_pending(self, depth: int) -> bool:
        return bool(self._queues.get(depth))

    @property
    def visited_count(self) -> int:
        return len(self._visited)
