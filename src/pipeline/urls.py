"""URL validation and resolution pipeline stage."""

from urllib.parse import urljoin, urlparse

from models.record import DirectoryRecord
from validation.collector import ValidationCollector


def _looks_like_url(url: str) -> bool:
    stripped = url.strip()
    if stripped.startswith(("http://", "https://", "/", "./", "../")):
        return True
    parsed = urlparse(stripped)
    return bool(parsed.scheme and parsed.netloc)


def _resolve_and_validate(url: str | None, base_url: str) -> tuple[str | None, bool]:
    if not url or not url.strip():
        return url, False
    if not _looks_like_url(url):
        return url, False
    resolved = urljoin(base_url, url.strip())
    parsed = urlparse(resolved)
    is_valid = bool(parsed.scheme in ("http", "https") and parsed.netloc)
    return resolved if is_valid else url, is_valid


def validate_urls(
    records: list[DirectoryRecord],
    collector: ValidationCollector,
) -> list[DirectoryRecord]:
    resolved_count = 0
    invalid_count = 0
    result = []

    for record in records:
        if record.website is None:
            result.append(record)
            continue

        new_url, is_valid = _resolve_and_validate(record.website, record.source_url)

        if is_valid:
            if new_url != record.website:
                resolved_count += 1
            else:
                resolved_count += 1
        else:
            invalid_count += 1
            collector.add_warning(
                "website",
                record.website,
                "Invalid URL format",
                record.source_url,
            )

        result.append(record.model_copy(update={"website": new_url}))

    collector.add_stat("urls_resolved", resolved_count)
    collector.add_stat("urls_invalid", invalid_count)
    return result
