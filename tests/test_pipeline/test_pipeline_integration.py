"""End-to-end integration test for the data quality pipeline."""

import csv
import json
from datetime import datetime, timezone

from models.record import DirectoryRecord
from pipeline import run_pipeline


def test_pipeline_produces_all_output_files(tmp_path):
    now = datetime.now(timezone.utc)
    records = [
        DirectoryRecord(
            region="Northeast",
            category="Restaurants",
            name="  Caf&eacute; &amp; Bar  ",
            address="123 Main St",
            phone="(415) 555-1234",
            website="/about",
            description="Great food\n\twith   extra space",
            source_url="https://example.com/listings/1",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Northeast",
            category="Restaurants",
            name="Cafe & Bar",
            address="123 Main St",
            phone=None,
            website=None,
            description=None,
            source_url="https://example.com/listings/2",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="Southwest",
            category="Hotels",
            name="Good Hotel",
            address="456 Oak Ave",
            phone="+44 20 8366 1177",
            website="https://goodhotel.com",
            description="Nice place",
            source_url="https://example.com/listings/3",
            scraped_at=now,
        ),
        DirectoryRecord(
            region="West",
            category="Shops",
            name="Bad Phone Shop",
            address="789 Elm St",
            phone="not-a-phone",
            website="not-a-url",
            description="Has invalid data",
            source_url="https://example.com/listings/4",
            scraped_at=now,
        ),
    ]

    config = {
        "default_country_code": "US",
        "base_url": "https://example.com",
        "output_dir": str(tmp_path),
    }

    final_records, collector = run_pipeline(records, config, tmp_path)

    # All 3 output files exist
    assert (tmp_path / "data.csv").exists()
    assert (tmp_path / "data.json").exists()
    assert (tmp_path / "validation_report.json").exists()

    # Fewer records than input (duplicates removed)
    assert len(final_records) < len(records)

    # CSV has BOM and correct columns
    csv_bytes = (tmp_path / "data.csv").read_bytes()
    assert csv_bytes[:3] == b"\xef\xbb\xbf"

    csv_text = (tmp_path / "data.csv").read_text(encoding="utf-8-sig")
    reader = csv.DictReader(csv_text.splitlines())
    csv_rows = list(reader)
    assert len(csv_rows) == len(final_records)

    # Phone numbers are normalized in CSV output
    phones_in_csv = [r["phone"] for r in csv_rows if r["phone"]]
    normalized_phones = [p for p in phones_in_csv if p.startswith("+")]
    assert len(normalized_phones) >= 1

    # JSON has nested hierarchy
    json_data = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    assert "metadata" in json_data
    assert "regions" in json_data
    assert json_data["metadata"]["total_records"] == len(final_records)

    # Report has accurate stats
    report = json.loads((tmp_path / "validation_report.json").read_text())
    assert report["record_counts"]["unique"] == len(final_records)
    assert report["record_counts"]["duplicates_removed"] >= 1
    assert "field_completeness" in report
    assert "normalization_stats" in report


def test_text_cleaning_applied_in_output(tmp_path):
    now = datetime.now(timezone.utc)
    records = [
        DirectoryRecord(
            region="Test",
            category="Test",
            name="  Caf&eacute;  ",
            source_url="https://example.com/1",
            scraped_at=now,
        ),
    ]
    config = {
        "default_country_code": "US",
        "base_url": "https://example.com",
        "output_dir": str(tmp_path),
    }

    final_records, _ = run_pipeline(records, config, tmp_path)
    assert final_records[0].name == "Caf\u00e9"
