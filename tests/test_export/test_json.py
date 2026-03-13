"""Tests for JSON export module."""

import json
from datetime import UTC, datetime

from export.json_export import export_json
from models.record import DirectoryRecord


def _make_record(**overrides):
    defaults = {
        "region": "Northeast",
        "category": "Restaurants",
        "name": "Test Cafe",
        "source_url": "https://example.com/1",
        "scraped_at": datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DirectoryRecord(**defaults)


class TestExportJson:
    def test_produces_valid_json(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_metadata_and_regions_keys(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "metadata" in data
        assert "regions" in data

    def test_metadata_fields(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data["metadata"]
        assert "scraped_at" in meta
        assert meta["target_url"] == "https://example.com"
        assert meta["total_records"] == 1
        assert meta["schema_version"] == "1.0"

    def test_groups_by_region_then_category(self, tmp_path):
        records = [
            _make_record(region="Northeast", category="Restaurants", name="A"),
            _make_record(region="Northeast", category="Hotels", name="B"),
            _make_record(region="Southwest", category="Restaurants", name="C"),
        ]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        regions = data["regions"]
        assert len(regions) == 2
        region_names = [r["name"] for r in regions]
        assert "Northeast" in region_names
        assert "Southwest" in region_names

    def test_region_has_name_and_categories(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        region = data["regions"][0]
        assert "name" in region
        assert "categories" in region

    def test_category_has_name_and_records(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        category = data["regions"][0]["categories"][0]
        assert "name" in category
        assert "records" in category

    def test_records_exclude_region_and_category(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        data = json.loads(path.read_text(encoding="utf-8"))
        record = data["regions"][0]["categories"][0]["records"][0]
        assert "region" not in record
        assert "category" not in record
        assert "name" in record

    def test_pretty_printed_with_indent(self, tmp_path):
        records = [_make_record()]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        text = path.read_text(encoding="utf-8")
        assert "  " in text  # 2-space indent

    def test_utf8_encoding_non_ascii(self, tmp_path):
        records = [_make_record(name="Caf\u00e9 Bar")]
        path = tmp_path / "data.json"
        export_json(records, path, "https://example.com")
        text = path.read_text(encoding="utf-8")
        assert "Caf\u00e9" in text  # not escaped as \u00e9
