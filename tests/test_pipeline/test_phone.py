"""Tests for phone normalization pipeline stage."""

from datetime import datetime, timezone

from models.record import DirectoryRecord
from pipeline.phone import normalize_phones
from validation.collector import ValidationCollector


def _make_record(**overrides):
    defaults = {
        "region": "Test",
        "category": "Test",
        "name": "Test",
        "source_url": "https://example.com",
        "scraped_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


class TestNormalizePhones:
    def test_normalizes_us_number(self, collector):
        records = [_make_record(phone="(415) 555-1234")]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone == "+14155551234"

    def test_normalizes_international_number(self, collector):
        records = [_make_record(phone="+44 20 8366 1177")]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone == "+442083661177"

    def test_keeps_invalid_number_as_is(self, collector):
        records = [_make_record(phone="not-a-phone")]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone == "not-a-phone"

    def test_adds_warning_for_invalid_number(self, collector):
        records = [_make_record(phone="not-a-phone")]
        normalize_phones(records, collector, "US")
        assert len(collector.warnings) == 1
        assert collector.warnings[0]["field"] == "phone"

    def test_keeps_none_phone_unchanged(self, collector):
        records = [_make_record(phone=None)]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone is None

    def test_keeps_empty_phone_unchanged(self, collector):
        records = [_make_record(phone="")]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone == ""

    def test_records_phones_normalized_stat(self, collector):
        records = [_make_record(phone="(415) 555-1234")]
        normalize_phones(records, collector, "US")
        assert collector.stats["phones_normalized"] == 1

    def test_records_phones_failed_stat(self, collector):
        records = [_make_record(phone="not-a-phone")]
        normalize_phones(records, collector, "US")
        assert collector.stats["phones_failed"] == 1

    def test_warning_reason_describes_issue(self, collector):
        records = [_make_record(phone="not-a-phone")]
        normalize_phones(records, collector, "US")
        reason = collector.warnings[0]["reason"].lower()
        assert "parse" in reason or "invalid" in reason

    def test_mixed_valid_and_invalid(self, collector):
        records = [
            _make_record(phone="(415) 555-1234"),
            _make_record(phone="not-a-phone"),
            _make_record(phone=None),
        ]
        result = normalize_phones(records, collector, "US")
        assert result[0].phone == "+14155551234"
        assert result[1].phone == "not-a-phone"
        assert result[2].phone is None
        assert collector.stats["phones_normalized"] == 1
        assert collector.stats["phones_failed"] == 1
