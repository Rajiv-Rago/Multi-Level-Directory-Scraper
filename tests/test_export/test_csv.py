"""Tests for CSV export module."""

import csv
from datetime import datetime, timezone

from models.record import DirectoryRecord
from export.csv_export import export_csv


def _make_record(**overrides):
    defaults = {
        "region": "Northeast",
        "category": "Restaurants",
        "name": "Test Cafe",
        "source_url": "https://example.com/1",
        "scraped_at": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


EXPECTED_COLUMNS = [
    "region", "category", "name", "address", "phone",
    "website", "description", "source_url", "scraped_at",
]


class TestExportCsv:
    def test_starts_with_utf8_bom(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        raw = path.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_header_row_column_order(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        reader = csv.reader(text.splitlines())
        header = next(reader)
        assert header == EXPECTED_COLUMNS

    def test_one_data_row_per_record(self, tmp_path):
        records = [_make_record(name="A"), _make_record(name="B")]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        reader = csv.reader(text.splitlines())
        next(reader)  # skip header
        rows = list(reader)
        assert len(rows) == 2

    def test_none_fields_as_empty_strings(self, tmp_path):
        records = [_make_record(address=None, phone=None)]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        row = next(reader)
        assert row["address"] == ""
        assert row["phone"] == ""

    def test_handles_commas_and_quotes(self, tmp_path):
        records = [_make_record(name='Cafe "The Best", Inc.')]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        row = next(reader)
        assert row["name"] == 'Cafe "The Best", Inc.'

    def test_serializes_datetime_as_iso(self, tmp_path):
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        records = [_make_record(scraped_at=ts)]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        row = next(reader)
        assert "2026-01-15" in row["scraped_at"]

    def test_no_extra_blank_lines(self, tmp_path):
        records = [_make_record(name="A"), _make_record(name="B")]
        path = tmp_path / "data.csv"
        export_csv(records, path)
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        assert len(lines) == 3  # header + 2 data rows
