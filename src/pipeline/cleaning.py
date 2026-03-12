"""Text cleaning pipeline stage."""

import html
import re

from models.record import DirectoryRecord
from validation.collector import ValidationCollector


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def clean_text_fields(
    records: list[DirectoryRecord],
    collector: ValidationCollector,
) -> list[DirectoryRecord]:
    cleaned = []
    for record in records:
        cleaned.append(record.model_copy(update={
            "name": _normalize_text(record.name),
            "address": _normalize_text(record.address),
            "description": _normalize_text(record.description),
        }))
    collector.add_stat("records_cleaned", len(records))
    return cleaned
