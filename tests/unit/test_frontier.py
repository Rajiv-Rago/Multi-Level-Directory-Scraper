"""Tests for URL frontier with deduplication and per-level queues."""

from scraper.frontier import FrontierItem, URLFrontier


class TestFrontierAdd:
    def test_add_new_url_returns_true(self):
        frontier = URLFrontier()
        assert frontier.add("https://example.com/a", depth=0) is True

    def test_add_duplicate_returns_false(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        assert frontier.add("https://example.com/a", depth=0) is False

    def test_add_normalized_duplicate_returns_false(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/path/", depth=0)
        assert frontier.add("https://example.com/path", depth=0) is False

    def test_add_with_ancestors(self):
        frontier = URLFrontier()
        ancestors = [{"level": "region", "label": "North", "url": "https://example.com/north"}]
        frontier.add("https://example.com/detail/1", depth=1, ancestors=ancestors)
        item = frontier.pop(1)
        assert item.ancestors == ancestors


class TestFrontierPop:
    def test_pop_returns_fifo_order(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        frontier.add("https://example.com/b", depth=0)
        assert frontier.pop(0).url == "https://example.com/a"
        assert frontier.pop(0).url == "https://example.com/b"

    def test_pop_empty_returns_none(self):
        frontier = URLFrontier()
        assert frontier.pop(0) is None

    def test_pop_returns_frontier_item(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        item = frontier.pop(0)
        assert isinstance(item, FrontierItem)
        assert item.url == "https://example.com/a"
        assert item.depth == 0
        assert item.ancestors == []


class TestFrontierHasPending:
    def test_has_pending_true(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        assert frontier.has_pending(0) is True

    def test_has_pending_false(self):
        frontier = URLFrontier()
        assert frontier.has_pending(0) is False

    def test_has_pending_after_pop(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        frontier.pop(0)
        assert frontier.has_pending(0) is False


class TestFrontierDepthIndependence:
    def test_different_depths_independent(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        frontier.add("https://example.com/b", depth=1)
        assert frontier.has_pending(0) is True
        assert frontier.has_pending(1) is True
        frontier.pop(0)
        assert frontier.has_pending(0) is False
        assert frontier.has_pending(1) is True


class TestFrontierVisitedCount:
    def test_visited_count(self):
        frontier = URLFrontier()
        frontier.add("https://example.com/a", depth=0)
        frontier.add("https://example.com/b", depth=0)
        frontier.add("https://example.com/a", depth=0)  # duplicate
        assert frontier.visited_count == 2
