"""Tests for URL validation and resolution pipeline stage."""

from datetime import datetime, timezone

import pytest

from models.record import DirectoryRecord
from pipeline.urls import validate_urls


def _make_record(**overrides):
    defaults = {
        "region": "Test",
        "category": "Test",
        "name": "Test",
        "source_url": "https://example.com/page",
        "scraped_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


class TestValidateUrls:
    def test_resolves_relative_url(self, collector):
        records = [_make_record(website="/about")]
        result = validate_urls(records, collector)
        assert result[0].website == "https://example.com/about"

    def test_resolves_parent_relative_url(self, collector):
        records = [_make_record(
            website="../other",
            source_url="https://example.com/dir/page",
        )]
        result = validate_urls(records, collector)
        assert result[0].website == "https://example.com/other"

    def test_keeps_absolute_url_unchanged(self, collector):
        records = [_make_record(website="https://example.com/page")]
        result = validate_urls(records, collector)
        assert result[0].website == "https://example.com/page"

    def test_flags_invalid_url(self, collector):
        records = [_make_record(website="not-a-url")]
        result = validate_urls(records, collector)
        assert result[0].website == "not-a-url"
        assert len(collector.warnings) == 1
        assert collector.warnings[0]["field"] == "website"

    def test_preserves_none_website(self, collector):
        records = [_make_record(website=None)]
        result = validate_urls(records, collector)
        assert result[0].website is None

    def test_records_urls_resolved_stat(self, collector):
        records = [_make_record(website="/about")]
        validate_urls(records, collector)
        assert collector.stats["urls_resolved"] == 1

    def test_records_urls_invalid_stat(self, collector):
        records = [_make_record(website="not-a-url")]
        validate_urls(records, collector)
        assert collector.stats["urls_invalid"] == 1

    @pytest.mark.parametrize("url,expected", [
        ("/about", "https://example.com/about"),
        ("./page2", "https://example.com/page2"),
        ("https://other.com", "https://other.com"),
    ])
    def test_various_url_resolutions(self, collector, url, expected):
        records = [_make_record(website=url)]
        result = validate_urls(records, collector)
        assert result[0].website == expected
