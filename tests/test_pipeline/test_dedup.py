"""Tests for deduplication pipeline stage."""

from datetime import datetime, timezone

from models.record import DirectoryRecord
from pipeline.dedup import deduplicate
from validation.collector import ValidationCollector


def _make_record(**overrides):
    defaults = {
        "region": "Test",
        "category": "Test",
        "name": "Test Record",
        "source_url": "https://example.com/1",
        "scraped_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


class TestDeduplicate:
    def test_removes_duplicate_by_name_and_address(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St", source_url="https://a.com"),
            _make_record(name="Cafe", address="123 Main St", source_url="https://b.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 1

    def test_keeps_record_with_more_complete_fields(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St", phone=None, website=None),
            _make_record(name="Cafe", address="123 Main St", phone="+1234", website="https://cafe.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 1
        assert result[0].phone == "+1234"
        assert result[0].website == "https://cafe.com"

    def test_uses_source_url_as_fallback_when_no_address(self, collector):
        records = [
            _make_record(name="Cafe", address=None, source_url="https://a.com"),
            _make_record(name="Cafe", address=None, source_url="https://b.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 2

    def test_normalizes_keys_case_insensitive(self, collector):
        records = [
            _make_record(name="Cafe Bar", address="123 Main St", source_url="https://a.com"),
            _make_record(name="CAFE BAR", address="123 MAIN ST", source_url="https://b.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 1

    def test_normalizes_keys_ignoring_punctuation(self, collector):
        records = [
            _make_record(name="Caf\u00e9 Bar", address="123 Main St.", source_url="https://a.com"),
            _make_record(name="cafe bar", address="123 Main St", source_url="https://b.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 1

    def test_logs_dedup_decisions(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St", source_url="https://a.com"),
            _make_record(name="Cafe", address="123 Main St", source_url="https://b.com"),
        ]
        deduplicate(records, collector)
        assert len(collector.warnings) == 1
        assert collector.warnings[0]["field"] == "duplicate"

    def test_records_duplicates_removed_stat(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St", source_url="https://a.com"),
            _make_record(name="Cafe", address="123 Main St", source_url="https://b.com"),
        ]
        deduplicate(records, collector)
        assert collector.stats["duplicates_removed"] == 1

    def test_returns_fewer_records_with_duplicates(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St", source_url="https://a.com"),
            _make_record(name="Cafe", address="123 Main St", source_url="https://b.com"),
            _make_record(name="Hotel", address="456 Oak Ave", source_url="https://c.com"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 2

    def test_preserves_all_records_when_no_duplicates(self, collector):
        records = [
            _make_record(name="Cafe", address="123 Main St"),
            _make_record(name="Hotel", address="456 Oak Ave"),
            _make_record(name="Shop", address="789 Elm St"),
        ]
        result = deduplicate(records, collector)
        assert len(result) == 3
        assert collector.stats.get("duplicates_removed", 0) == 0
