"""JSON export with nested region/category hierarchy."""

import json
from datetime import UTC, datetime
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from models.record import DirectoryRecord


def export_json(records: list[DirectoryRecord], output_path: Path, base_url: str) -> None:
    output = {
        "metadata": {
            "scraped_at": datetime.now(UTC).isoformat(),
            "target_url": base_url,
            "total_records": len(records),
            "schema_version": "1.0",
        },
        "regions": [],
    }

    sorted_records = sorted(records, key=attrgetter("region", "category"))
    for region, region_records in groupby(sorted_records, key=attrgetter("region")):
        region_data = {"name": region, "categories": []}
        for category, cat_records in groupby(region_records, key=attrgetter("category")):
            region_data["categories"].append({
                "name": category,
                "records": [
                    r.model_dump(mode="json", exclude={"region", "category"})
                    for r in cat_records
                ],
            })
        output["regions"].append(region_data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
