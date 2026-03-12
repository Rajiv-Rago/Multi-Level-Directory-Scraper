"""Validation report writer and stdout summary."""

import json
from datetime import datetime, timezone
from pathlib import Path

from models.record import DirectoryRecord
from validation.collector import ValidationCollector

TRACKED_FIELDS = ["name", "address", "phone", "website", "description"]


def _field_completeness(records: list[DirectoryRecord]) -> dict:
    total = len(records)
    completeness = {}
    for field_name in TRACKED_FIELDS:
        present = sum(1 for r in records if getattr(r, field_name) is not None)
        missing = total - present
        percentage = (present / total * 100) if total > 0 else 0.0
        completeness[field_name] = {
            "count_present": present,
            "count_missing": missing,
            "percentage": round(percentage, 1),
        }
    return completeness


def write_report(
    collector: ValidationCollector,
    records: list[DirectoryRecord],
    output_path: Path,
    config: dict,
) -> dict:
    duplicates_removed = collector.stats.get("duplicates_removed", 0)
    report = {
        "run_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(collector.duration_seconds, 2),
            "config_used": config,
        },
        "record_counts": {
            "total": len(records) + duplicates_removed,
            "unique": len(records),
            "duplicates_removed": duplicates_removed,
        },
        "field_completeness": _field_completeness(records),
        "normalization_stats": {
            "phones_normalized": collector.stats.get("phones_normalized", 0),
            "phones_failed": collector.stats.get("phones_failed", 0),
            "urls_resolved": collector.stats.get("urls_resolved", 0),
            "urls_invalid": collector.stats.get("urls_invalid", 0),
        },
        "warnings": collector.warnings,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return report


def print_summary(collector: ValidationCollector, records: list[DirectoryRecord]) -> None:
    duplicates_removed = collector.stats.get("duplicates_removed", 0)
    total = len(records) + duplicates_removed
    unique = len(records)

    completeness = _field_completeness(records)
    avg_completeness = (
        sum(f["percentage"] for f in completeness.values()) / len(completeness)
        if completeness
        else 0.0
    )

    phones_ok = collector.stats.get("phones_normalized", 0)
    phones_fail = collector.stats.get("phones_failed", 0)
    urls_ok = collector.stats.get("urls_resolved", 0)
    urls_fail = collector.stats.get("urls_invalid", 0)
    warning_count = len(collector.warnings)
    duration = collector.duration_seconds

    bar = "\u2550" * 51
    print(f" {bar}")
    print("  Data Quality Report")
    print(f" {bar}")
    print(f"  Records:      {total} total, {unique} unique, {duplicates_removed} duplicates removed")
    print(f"  Completeness: {avg_completeness:.1f}% field completeness")
    print(f"  Phones:       {phones_ok} normalized, {phones_fail} failed")
    print(f"  URLs:         {urls_ok} resolved, {urls_fail} invalid")
    print(f"  Warnings:     {warning_count} total")
    print(f"  Duration:     {duration:.2f}s")
    print(f" {bar}")
