"""Tests for ancestor context propagation through crawl levels."""

import pytest

from scraper.frontier import URLFrontier


class TestAncestorPropagation:
    def test_ancestors_grow_through_levels(self):
        frontier = URLFrontier()
        frontier.add("https://example.com", depth=0)
        item0 = frontier.pop(0)
        assert item0.ancestors == []

        ancestors_for_depth1 = item0.ancestors + [
            {"level": "region", "label": "North", "url": "https://example.com"}
        ]
        frontier.add("https://example.com/north", depth=1, ancestors=ancestors_for_depth1)
        item1 = frontier.pop(1)
        assert len(item1.ancestors) == 1
        assert item1.ancestors[0]["level"] == "region"

        ancestors_for_depth2 = item1.ancestors + [
            {"level": "category", "label": "Restaurants", "url": "https://example.com/north"}
        ]
        frontier.add("https://example.com/north/rest", depth=2, ancestors=ancestors_for_depth2)
        item2 = frontier.pop(2)
        assert len(item2.ancestors) == 2
        assert item2.ancestors[0]["label"] == "North"
        assert item2.ancestors[1]["label"] == "Restaurants"

    def test_empty_ancestors_for_seed(self):
        frontier = URLFrontier()
        frontier.add("https://example.com", depth=0)
        item = frontier.pop(0)
        assert item.ancestors == []

    def test_ancestor_label_preserved(self):
        frontier = URLFrontier()
        ancestors = [{"level": "region", "label": "West Coast", "url": "https://example.com/west"}]
        frontier.add("https://example.com/detail/1", depth=1, ancestors=ancestors)
        item = frontier.pop(1)
        assert item.ancestors[0]["label"] == "West Coast"
