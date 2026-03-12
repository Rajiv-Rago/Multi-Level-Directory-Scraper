"""CSV export with UTF-8 BOM for Excel compatibility."""

import csv
from pathlib import Path

from models.record import DirectoryRecord

COLUMNS = [
    "region", "category", "name", "address", "phone",
    "website", "description", "source_url", "scraped_at",
]


def export_csv(records: list[DirectoryRecord], output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            for key in COLUMNS:
                if row.get(key) is None:
                    row[key] = ""
            writer.writerow(row)
