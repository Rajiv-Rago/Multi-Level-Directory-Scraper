"""Data quality pipeline runner."""

from pathlib import Path

from export.csv_export import export_csv
from export.json_export import export_json
from export.report import print_summary, write_report
from models.record import DirectoryRecord
from pipeline.cleaning import clean_text_fields
from pipeline.dedup import deduplicate
from pipeline.phone import normalize_phones
from pipeline.urls import validate_urls
from validation.collector import ValidationCollector


def run_pipeline(
    records: list[DirectoryRecord],
    config: dict,
    output_dir: Path,
) -> tuple[list[DirectoryRecord], ValidationCollector]:
    collector = ValidationCollector()

    records = clean_text_fields(records, collector)
    records = normalize_phones(records, collector, config["default_country_code"])
    records = validate_urls(records, collector)
    records = deduplicate(records, collector)

    export_csv(records, output_dir / "data.csv")
    export_json(records, output_dir / "data.json", config["base_url"])
    write_report(collector, records, output_dir / "validation_report.json", config)
    print_summary(collector, records)

    return records, collector
