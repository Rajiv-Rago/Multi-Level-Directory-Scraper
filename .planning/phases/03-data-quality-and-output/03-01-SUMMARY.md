# Plan 03-01 Summary: Pipeline Core

**Status:** Complete
**Completed:** 2026-03-13
**Tests:** 37 passing

## What Was Built

### Models and Infrastructure
- `src/models/record.py` — `DirectoryRecord` pydantic model with all entity fields (region, category, name, address, phone, website, description, source_url, scraped_at)
- `src/validation/collector.py` — `ValidationCollector` dataclass that accumulates warnings and stats across pipeline stages

### Pipeline Stages (4 composable functions)
- `src/pipeline/cleaning.py` — `clean_text_fields()`: strips whitespace, decodes HTML entities, collapses internal whitespace. Leaves phone/website untouched.
- `src/pipeline/phone.py` — `normalize_phones()`: E.164 normalization via phonenumbers library. Invalid numbers preserved as-is with warnings.
- `src/pipeline/urls.py` — `validate_urls()`: resolves relative URLs against source_url, validates scheme+netloc. Invalid URLs preserved with warnings.
- `src/pipeline/dedup.py` — `deduplicate()`: composite key (normalized name + address), NFKD Unicode decomposition for accent-insensitive matching, keeps most complete record.

## Key Design Decisions
- NFKD decomposition (not NFC) in dedup to strip accents for matching ("Cafe" == "Cafe")
- URL validation uses heuristic `_looks_like_url()` to avoid `urljoin` treating plaintext as relative paths
- All stages return new record lists (immutable via `model_copy`), never mutate inputs

## Requirements Covered
- VAL-01: Phone normalization to E.164 (test_phone.py)
- VAL-02: URL validation and resolution (test_urls.py)
- VAL-03: Composite key deduplication (test_dedup.py)
- VAL-04: Text cleaning — whitespace, HTML entities (test_cleaning.py)
