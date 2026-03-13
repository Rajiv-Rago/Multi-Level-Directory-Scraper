"""Tests for validation report and stdout summary."""

import json
from datetime import UTC, datetime

from export.report import print_summary, write_report
from models.record import DirectoryRecord
from validation.collector import ValidationCollector


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


class TestWriteReport:
    def test_produces_valid_json(self, tmp_path):
        collector = ValidationCollector()
        records = [_make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {"base_url": "https://example.com"})
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_contains_run_metadata(self, tmp_path):
        collector = ValidationCollector()
        records = [_make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {"base_url": "https://example.com"})
        data = json.loads(path.read_text())
        meta = data["run_metadata"]
        assert "timestamp" in meta
        assert "duration_seconds" in meta
        assert "config_used" in meta

    def test_contains_record_counts(self, tmp_path):
        collector = ValidationCollector()
        collector.add_stat("duplicates_removed", 2)
        records = [_make_record(), _make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {})
        data = json.loads(path.read_text())
        counts = data["record_counts"]
        assert counts["total"] == 4  # 2 unique + 2 removed
        assert counts["unique"] == 2
        assert counts["duplicates_removed"] == 2

    def test_contains_field_completeness(self, tmp_path):
        collector = ValidationCollector()
        records = [
            _make_record(address="123 Main", phone="+1234", website="https://a.com", description="desc"),
            _make_record(address=None, phone=None, website=None, description=None),
        ]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {})
        data = json.loads(path.read_text())
        completeness = data["field_completeness"]
        assert "address" in completeness
        assert completeness["address"]["count_present"] == 1
        assert completeness["address"]["count_missing"] == 1
        assert completeness["address"]["percentage"] == 50.0

    def test_field_completeness_covers_all_fields(self, tmp_path):
        collector = ValidationCollector()
        records = [_make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {})
        data = json.loads(path.read_text())
        completeness = data["field_completeness"]
        for field_name in ["name", "address", "phone", "website", "description"]:
            assert field_name in completeness

    def test_contains_normalization_stats(self, tmp_path):
        collector = ValidationCollector()
        collector.add_stat("phones_normalized", 5)
        collector.add_stat("phones_failed", 1)
        collector.add_stat("urls_resolved", 3)
        collector.add_stat("urls_invalid", 2)
        records = [_make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {})
        data = json.loads(path.read_text())
        stats = data["normalization_stats"]
        assert stats["phones_normalized"] == 5
        assert stats["phones_failed"] == 1
        assert stats["urls_resolved"] == 3
        assert stats["urls_invalid"] == 2

    def test_contains_warnings(self, tmp_path):
        collector = ValidationCollector()
        collector.add_warning("phone", "bad", "parse error", "https://example.com")
        records = [_make_record()]
        path = tmp_path / "report.json"
        write_report(collector, records, path, {})
        data = json.loads(path.read_text())
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["field"] == "phone"

    def test_returns_report_dict(self, tmp_path):
        collector = ValidationCollector()
        records = [_make_record()]
        path = tmp_path / "report.json"
        result = write_report(collector, records, path, {})
        assert isinstance(result, dict)
        assert "run_metadata" in result


class TestPrintSummary:
    def test_outputs_total_records(self, capsys):
        collector = ValidationCollector()
        collector.add_stat("duplicates_removed", 1)
        records = [_make_record(), _make_record()]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "3" in captured.out  # 2 unique + 1 removed = 3 total

    def test_outputs_unique_records(self, capsys):
        collector = ValidationCollector()
        records = [_make_record(), _make_record()]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "2" in captured.out

    def test_outputs_duplicates_removed(self, capsys):
        collector = ValidationCollector()
        collector.add_stat("duplicates_removed", 3)
        records = [_make_record()]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "3" in captured.out

    def test_outputs_field_completeness_percentage(self, capsys):
        collector = ValidationCollector()
        records = [
            _make_record(address="a", phone="p", website="w", description="d"),
        ]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "%" in captured.out

    def test_outputs_duration(self, capsys):
        collector = ValidationCollector()
        records = [_make_record()]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "s" in captured.out.lower()

    def test_is_human_readable(self, capsys):
        collector = ValidationCollector()
        records = [_make_record()]
        print_summary(collector, records)
        captured = capsys.readouterr()
        assert "Data Quality Report" in captured.out
