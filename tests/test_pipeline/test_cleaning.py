"""Tests for text cleaning pipeline stage."""

from datetime import UTC, datetime

from models.record import DirectoryRecord
from pipeline.cleaning import clean_text_fields


def _make_record(**overrides):
    defaults = {
        "region": "Test",
        "category": "Test",
        "name": "Test",
        "source_url": "https://example.com",
        "scraped_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


class TestCleanTextFields:
    def test_strips_leading_trailing_whitespace(self, collector):
        records = [_make_record(name="  Foo Bar  ")]
        result = clean_text_fields(records, collector)
        assert result[0].name == "Foo Bar"

    def test_decodes_html_entities(self, collector):
        records = [_make_record(name="Caf&eacute; &amp; Bar")]
        result = clean_text_fields(records, collector)
        assert result[0].name == "Caf\u00e9 & Bar"

    def test_collapses_internal_whitespace(self, collector):
        records = [_make_record(name="Foo   Bar\n\tBaz")]
        result = clean_text_fields(records, collector)
        assert result[0].name == "Foo Bar Baz"

    def test_preserves_none_values(self, collector):
        records = [_make_record(address=None, description=None)]
        result = clean_text_fields(records, collector)
        assert result[0].address is None
        assert result[0].description is None

    def test_cleans_all_text_fields(self, collector):
        records = [_make_record(
            name="  Name  ",
            address="  Addr  ",
            description="  Desc  ",
        )]
        result = clean_text_fields(records, collector)
        assert result[0].name == "Name"
        assert result[0].address == "Addr"
        assert result[0].description == "Desc"

    def test_returns_same_count(self, collector, sample_records):
        result = clean_text_fields(sample_records, collector)
        assert len(result) == len(sample_records)

    def test_updates_collector_stats(self, collector, sample_records):
        clean_text_fields(sample_records, collector)
        assert collector.stats["records_cleaned"] == len(sample_records)

    def test_does_not_modify_phone_or_website(self, collector):
        records = [_make_record(phone="  (415) 555-1234  ", website="  /about  ")]
        result = clean_text_fields(records, collector)
        assert result[0].phone == "  (415) 555-1234  "
        assert result[0].website == "  /about  "
