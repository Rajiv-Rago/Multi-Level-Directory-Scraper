"""Deduplication pipeline stage."""

import re
import unicodedata

from models.record import DirectoryRecord
from validation.collector import ValidationCollector


def _normalize_for_dedup(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.casefold()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _make_dedup_key(record: DirectoryRecord) -> str:
    if record.address:
        return _normalize_for_dedup(record.name) + "|" + _normalize_for_dedup(record.address)
    return record.source_url


def _completeness_score(record: DirectoryRecord) -> int:
    fields = [record.address, record.phone, record.website, record.description]
    return sum(1 for f in fields if f is not None)


def deduplicate(
    records: list[DirectoryRecord],
    collector: ValidationCollector,
) -> list[DirectoryRecord]:
    groups: dict[str, list[DirectoryRecord]] = {}
    for record in records:
        key = _make_dedup_key(record)
        groups.setdefault(key, []).append(record)

    result = []
    duplicates_removed = 0

    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue

        best = max(group, key=_completeness_score)
        result.append(best)

        for record in group:
            if record is not best:
                duplicates_removed += 1
                collector.add_warning(
                    "duplicate",
                    record.name,
                    f"Duplicate of {best.name} (kept: {best.source_url})",
                    record.source_url,
                )

    collector.add_stat("duplicates_removed", duplicates_removed)
    return result
