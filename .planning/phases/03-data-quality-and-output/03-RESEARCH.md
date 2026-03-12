# Phase 3: Data Quality and Output - Research

**Researched:** 2026-03-13
**Domain:** Data cleaning pipeline, phone normalization, deduplication, CSV/JSON export
**Confidence:** HIGH

## Summary

Phase 3 transforms raw extracted records from Phase 2 into clean, validated output files. The pipeline is a linear sequence of composable functions: text cleaning, phone normalization, URL validation, deduplication, then export (CSV + JSON + validation report). Each stage takes records in and returns records out.

The stack is well-established Python: `phonenumbers` for E.164 normalization, `pydantic` for record schema and validation, Python's built-in `csv` module with `utf-8-sig` encoding for Excel-compatible CSV, and `json` module for nested JSON export. No exotic dependencies are needed -- this is standard data engineering.

**Primary recommendation:** Build each pipeline stage as a pure function operating on a list of pydantic models, with a shared `ValidationCollector` accumulating warnings/stats throughout. Keep it simple -- no framework, no async, no streaming.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phone normalization to E.164 format using `phonenumbers` library with default country code from site config
- Numbers that cannot be parsed kept as-is with warning (never discard data)
- Relative URLs resolved to absolute using source page URL as base; validated as well-formed
- Invalid URLs kept in output but flagged (never discard data)
- Strip whitespace, decode HTML entities, collapse internal whitespace runs
- Text cleaning applied uniformly before other validation steps
- Composite dedup key: normalized(name) + normalized(address), fallback source_url
- Dedup normalization: lowercase, strip whitespace, remove punctuation
- Keep record with most complete fields on duplicate
- Log every dedup decision with both records' source_urls
- Dedup runs after all cleaning/normalization
- CSV: UTF-8 with BOM, columns in specified order, RFC 4180 quoting, output as `data.csv`
- JSON: nested hierarchy with metadata object, pretty-printed 2-space indent, output as `data.json`
- Validation report: JSON format (`validation_report.json`), machine-readable with specified sections
- Human-readable summary to stdout at end of run
- Pipeline order: text cleaning -> phone normalization -> URL validation -> deduplication -> export
- Pydantic models for record schema
- Each pipeline stage is a composable function (records in, records out)
- Validation issues accumulate in a report collector
- Operates on full record set in memory

### Claude's Discretion
- Internal architecture of the ValidationCollector
- How to structure the pipeline module(s) and file organization
- Specific pydantic model field definitions and validators
- Implementation of the stdout summary formatting
- Test structure and fixture design

### Deferred Ideas (OUT OF SCOPE)
- NDJSON output for streaming pipelines (OUT-V2-01)
- Database storage
- JSON schema validation of output files
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VAL-01 | Phone numbers normalized to E.164 | `phonenumbers` library with `parse()` + `format_number()` + `PhoneNumberFormat.E164` |
| VAL-02 | URLs validated, relative resolved to absolute | `urllib.parse.urljoin()` for resolution, `urllib.parse.urlparse()` for validation |
| VAL-03 | Duplicates detected by composite key and deduplicated | Composable dedup function with normalized key generation |
| VAL-04 | Whitespace stripped, HTML entities decoded | `html.unescape()` + `str.strip()` + regex whitespace collapse |
| VAL-05 | Validation summary report produced | ValidationCollector accumulates stats, writes `validation_report.json` |
| VAL-06 | CSV opens cleanly in Excel/Sheets with UTF-8 BOM | `csv.writer` with `encoding='utf-8-sig'` and `newline=''` |
| OUT-01 | CSV with specified columns | `csv.DictWriter` with fieldnames in specified order |
| OUT-02 | JSON with nested region/category structure | Group records by region/category, `json.dump` with `indent=2` |
| OUT-03 | Validation report file with summary statistics | `validation_report.json` with run metadata, counts, field completeness, warnings |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| phonenumbers | 8.13+ | Phone number parsing, validation, E.164 formatting | Google's libphonenumber port; industry standard, handles 200+ country formats |
| pydantic | 2.10+ | Record schema definition, validation, serialization | Type-safe models with `model_dump()` for dict/JSON; Rust-powered v2 is 5-50x faster than v1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| csv (stdlib) | - | CSV writing with RFC 4180 compliance | Always -- built-in, battle-tested, no dependency needed |
| json (stdlib) | - | JSON serialization with pretty-printing | Always -- built-in, handles nested structures natively |
| html (stdlib) | - | `html.unescape()` for HTML entity decoding | Text cleaning stage -- decodes `&amp;`, `&#x27;`, etc. |
| urllib.parse (stdlib) | - | `urljoin()` for URL resolution, `urlparse()` for validation | URL validation stage -- resolves relative URLs against base |
| re (stdlib) | - | Regex for whitespace collapsing and dedup normalization | Text cleaning and dedup key generation |
| unicodedata (stdlib) | - | Unicode normalization for dedup key comparison | Optional -- NFC normalization before string comparison |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| phonenumbers | Manual regex | Regex can't handle 200+ country formats; phonenumbers is the standard |
| pydantic | dataclasses | Dataclasses lack built-in validation, serialization to JSON, field validators |
| csv (stdlib) | pandas.to_csv | Adds massive dependency for simple CSV writing; overkill for this use case |
| html.unescape | BeautifulSoup | BS4 is heavier; `html.unescape()` handles standard entities perfectly |

**Installation:**
```bash
pip install phonenumbers pydantic
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── models/
│   └── record.py          # Pydantic models: DirectoryRecord, ValidationWarning
├── pipeline/
│   ├── __init__.py         # Pipeline runner (orchestrates stages)
│   ├── cleaning.py         # Text cleaning stage
│   ├── phone.py            # Phone normalization stage
│   ├── urls.py             # URL validation/resolution stage
│   └── dedup.py            # Deduplication stage
├── export/
│   ├── csv_export.py       # CSV writer (UTF-8 BOM)
│   ├── json_export.py      # JSON writer (nested hierarchy)
│   └── report.py           # Validation report writer + stdout summary
└── validation/
    └── collector.py        # ValidationCollector (accumulates warnings/stats)
```

### Pattern 1: Composable Pipeline Stages
**What:** Each stage is a function: `(list[Record], ValidationCollector) -> list[Record]`
**When to use:** Every pipeline stage follows this signature for composability
**Example:**
```python
from models.record import DirectoryRecord
from validation.collector import ValidationCollector

def clean_text_fields(
    records: list[DirectoryRecord],
    collector: ValidationCollector,
) -> list[DirectoryRecord]:
    cleaned = []
    for record in records:
        # Apply cleaning to each text field
        cleaned_record = record.model_copy(update={
            "name": normalize_text(record.name),
            "address": normalize_text(record.address) if record.address else None,
            # ... other fields
        })
        cleaned.append(cleaned_record)
    collector.add_stat("text_fields_cleaned", len(records))
    return cleaned
```

### Pattern 2: ValidationCollector as Pipeline Context
**What:** A mutable object passed through all stages that accumulates warnings, stats, and timing
**When to use:** Every stage reports its findings to the collector instead of logging directly
**Example:**
```python
import time
from dataclasses import dataclass, field

@dataclass
class ValidationCollector:
    warnings: list[dict] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def add_warning(self, field_name: str, value: str, reason: str, source_url: str):
        self.warnings.append({
            "field": field_name,
            "value": value,
            "reason": reason,
            "source_url": source_url,
        })

    def add_stat(self, key: str, count: int):
        self.stats[key] = self.stats.get(key, 0) + count

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.start_time
```

### Pattern 3: Pipeline Runner
**What:** A function that chains all stages in order and handles the export step
**When to use:** Main entry point for post-processing
**Example:**
```python
def run_pipeline(
    records: list[DirectoryRecord],
    config: SiteConfig,
    output_dir: Path,
) -> ValidationCollector:
    collector = ValidationCollector()

    # Pipeline stages in order
    records = clean_text_fields(records, collector)
    records = normalize_phones(records, collector, config.default_country_code)
    records = validate_urls(records, collector)
    records = deduplicate(records, collector)

    # Export
    export_csv(records, output_dir / "data.csv")
    export_json(records, output_dir / "data.json", config)
    write_report(collector, records, output_dir / "validation_report.json")
    print_summary(collector, records)

    return collector
```

### Anti-Patterns to Avoid
- **Mutating records in place:** Use `model_copy(update={...})` to create new pydantic instances. Immutable records are easier to debug and test.
- **Logging instead of collecting:** Don't scatter `logger.warning()` calls. Accumulate everything in the collector so the report is complete.
- **Dedup before cleaning:** Always clean first. Comparing raw strings produces false negatives (e.g., "  Foo Bar " vs "Foo Bar").
- **Over-abstracting the pipeline:** Don't build a generic pipeline framework. A simple sequence of function calls in `run_pipeline()` is clearer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Phone number parsing | Regex-based phone parser | `phonenumbers.parse()` + `format_number()` | 200+ country formats, edge cases like extensions, vanity numbers |
| HTML entity decoding | Manual `&amp;` replacement | `html.unescape()` | Handles named entities, numeric entities, hex entities correctly |
| URL resolution | String concatenation for relative URLs | `urllib.parse.urljoin()` | Correctly handles `../`, query strings, fragments, protocol-relative URLs |
| CSV quoting | Manual escaping of commas/quotes | `csv.writer` with default quoting | RFC 4180 compliance, handles edge cases like embedded newlines |
| Unicode normalization | Custom lowercase/strip | `unicodedata.normalize('NFC', s).lower().strip()` | Handles combining characters, accented chars in dedup keys |

**Key insight:** Every "simple" text operation has Unicode edge cases. Use stdlib functions that handle them.

## Common Pitfalls

### Pitfall 1: CSV Without BOM Breaks Excel
**What goes wrong:** Excel opens the CSV and shows garbled international characters
**Why it happens:** Excel defaults to Windows-1252 encoding unless it sees a UTF-8 BOM at the start of the file
**How to avoid:** Use `encoding='utf-8-sig'` when opening the file for writing. Python's `utf-8-sig` codec automatically prepends the BOM (bytes `EF BB BF`).
**Warning signs:** Non-ASCII characters (accents, CJK, etc.) display as `Ã©` or `â€™` in Excel

### Pitfall 2: CSV newline Parameter
**What goes wrong:** Extra blank lines between rows on Windows
**Why it happens:** Python's `csv` module handles line endings itself; if `open()` also translates `\n` to `\r\n`, you get double line endings
**How to avoid:** Always pass `newline=''` to `open()` when writing CSV:
```python
with open(path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
```
**Warning signs:** Blank rows between every data row when opened in a text editor

### Pitfall 3: phonenumbers.parse() Requires Region for Local Numbers
**What goes wrong:** `NumberParseException` when parsing numbers without country code prefix
**Why it happens:** `phonenumbers.parse("020 8366 1177", None)` fails because without `+` prefix, the library needs a default region
**How to avoid:** Always pass the `default_region` parameter from site config:
```python
try:
    parsed = phonenumbers.parse(number_str, default_country_code)
    if phonenumbers.is_valid_number(parsed):
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    else:
        collector.add_warning("phone", number_str, "Invalid phone number pattern", source_url)
        return number_str  # Keep original
except phonenumbers.NumberParseException:
    collector.add_warning("phone", number_str, "Could not parse phone number", source_url)
    return number_str  # Keep original
```
**Warning signs:** Lots of parse exceptions in logs for numbers that look valid

### Pitfall 4: Dedup Key Normalization Inconsistency
**What goes wrong:** Duplicates slip through because keys aren't normalized the same way
**Why it happens:** One record has `"Café Bar"` and another has `"CAFÉ BAR"` -- if normalization doesn't handle Unicode casefolding, they won't match
**How to avoid:** Use a consistent normalization function for all key components:
```python
import re
import unicodedata

def normalize_for_dedup(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.casefold()  # casefold() > lower() for Unicode
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text
```
**Warning signs:** Duplicate count is suspiciously low; manual spot-check reveals obvious duplicates

### Pitfall 5: urljoin Edge Cases
**What goes wrong:** Resolved URLs are wrong for certain relative paths
**Why it happens:** `urljoin("https://example.com/dir/page.html", "//other.com/path")` produces `https://other.com/path` (protocol-relative URLs inherit scheme)
**How to avoid:** After `urljoin()`, validate the result has a proper scheme and host. Flag protocol-relative URLs that resolve to different domains.
**Warning signs:** URLs in output point to unexpected domains

### Pitfall 6: JSON Serialization of datetime
**What goes wrong:** `TypeError: Object of type datetime is not JSON serializable`
**Why it happens:** `scraped_at` timestamps are datetime objects that `json.dump()` can't handle
**How to avoid:** Use pydantic's `model_dump(mode='json')` which auto-serializes datetimes, or provide a `default` handler:
```python
json.dump(data, f, indent=2, default=str)
```
**Warning signs:** Pipeline crashes at the export stage with TypeError

## Code Examples

Verified patterns from official sources:

### Phone Number Normalization (E.164)
```python
# Source: phonenumbers official docs (Context7)
import phonenumbers

def normalize_phone(number_str: str, default_region: str) -> tuple[str, bool]:
    """Returns (formatted_number, was_normalized)."""
    if not number_str or not number_str.strip():
        return number_str, False
    try:
        parsed = phonenumbers.parse(number_str.strip(), default_region)
        if phonenumbers.is_valid_number(parsed):
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            return formatted, True
        return number_str, False  # Keep original, flag invalid
    except phonenumbers.NumberParseException:
        return number_str, False  # Keep original, flag unparseable
```

### CSV Export with UTF-8 BOM
```python
# Source: Python stdlib docs + verified web search
import csv
from pathlib import Path

COLUMNS = [
    "region", "category", "name", "address", "phone",
    "website", "description", "source_url", "scraped_at",
]

def export_csv(records: list, output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for record in records:
            writer.writerow(record.model_dump(mode='json'))
```

### JSON Export with Nested Hierarchy
```python
# Source: pydantic model_dump (Context7) + json stdlib
import json
from pathlib import Path
from datetime import datetime, timezone
from itertools import groupby
from operator import attrgetter

def export_json(records: list, output_path: Path, config) -> None:
    # Group by region, then category
    output = {
        "metadata": {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "target_url": config.base_url,
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
                "records": [r.model_dump(mode='json', exclude={"region", "category"}) for r in cat_records],
            })
        output["regions"].append(region_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
```

### Pydantic Record Model
```python
# Source: pydantic v2 docs (Context7)
from datetime import datetime
from pydantic import BaseModel

class DirectoryRecord(BaseModel):
    region: str
    category: str
    name: str
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    description: str | None = None
    source_url: str
    scraped_at: datetime
```

### URL Resolution and Validation
```python
# Source: Python urllib.parse stdlib
from urllib.parse import urljoin, urlparse

def resolve_and_validate_url(url: str | None, base_url: str) -> tuple[str | None, bool]:
    """Returns (resolved_url, is_valid)."""
    if not url or not url.strip():
        return url, False
    resolved = urljoin(base_url, url.strip())
    parsed = urlparse(resolved)
    is_valid = bool(parsed.scheme in ('http', 'https') and parsed.netloc)
    return resolved, is_valid
```

### Text Cleaning
```python
# Source: Python stdlib (html, re)
import html
import re

def normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text if text else None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydantic v1 with `dict()` | pydantic v2 with `model_dump()` | 2023 (pydantic v2 release) | 5-50x faster validation, `model_dump(mode='json')` for JSON-safe output |
| `str.lower()` for case normalization | `str.casefold()` for Unicode-aware folding | Python 3.3+ | Correctly handles German `ß` -> `ss`, Turkish `İ` -> `i`, etc. |
| Manual BOM byte writing | `encoding='utf-8-sig'` | Python 3.0+ | Automatic BOM handling, cleaner code |
| pandas for CSV export | stdlib `csv` module | Always available | No dependency, equally capable for simple writes |

**Deprecated/outdated:**
- pydantic v1 API (`.dict()`, `.json()`, `@validator`): Use v2 API (`.model_dump()`, `.model_dump_json()`, `@field_validator`)
- `phonenumbers` `prnt()` utility: Use standard `print()`; `prnt()` was for Python 2/3 compat

## Open Questions

1. **Record schema from Phase 2**
   - What we know: Phase 2 will extract records with fields defined in site config (name, address, phone, website, category, description, source_url, scraped_at)
   - What's unclear: Whether Phase 2 will output raw dicts or pydantic models
   - Recommendation: Define the pydantic model in Phase 3. Accept either dicts or models as input (pydantic can validate dicts into models). This decouples from Phase 2's implementation.

2. **Site config structure for default_country_code**
   - What we know: Phase 1 defines YAML config; default country code is a required field
   - What's unclear: Exact config key name and structure
   - Recommendation: Use `config.default_country_code` as the interface. Adapt if Phase 1 uses a different key.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | None -- Wave 0 will create `pyproject.toml` with `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_pipeline/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAL-01 | Phone numbers normalized to E.164 | unit | `pytest tests/test_pipeline/test_phone.py -x` | No -- Wave 0 |
| VAL-02 | URLs validated and resolved to absolute | unit | `pytest tests/test_pipeline/test_urls.py -x` | No -- Wave 0 |
| VAL-03 | Duplicates detected and deduplicated | unit | `pytest tests/test_pipeline/test_dedup.py -x` | No -- Wave 0 |
| VAL-04 | Whitespace stripped, HTML entities decoded | unit | `pytest tests/test_pipeline/test_cleaning.py -x` | No -- Wave 0 |
| VAL-05 | Validation report produced with stats | integration | `pytest tests/test_pipeline/test_report.py -x` | No -- Wave 0 |
| VAL-06 | CSV opens cleanly in Excel (UTF-8 BOM) | unit | `pytest tests/test_export/test_csv.py -x` | No -- Wave 0 |
| OUT-01 | CSV with correct columns | unit | `pytest tests/test_export/test_csv.py -x` | No -- Wave 0 |
| OUT-02 | JSON with nested hierarchy | unit | `pytest tests/test_export/test_json.py -x` | No -- Wave 0 |
| OUT-03 | Validation report file | integration | `pytest tests/test_pipeline/test_report.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pipeline/ -x -q` (< 5 seconds)
- **Per wave merge:** `pytest tests/ -v` (< 15 seconds)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- pytest config section `[tool.pytest.ini_options]`
- [ ] `tests/conftest.py` -- shared fixtures (sample records, sample config)
- [ ] `tests/test_pipeline/test_cleaning.py` -- covers VAL-04
- [ ] `tests/test_pipeline/test_phone.py` -- covers VAL-01
- [ ] `tests/test_pipeline/test_urls.py` -- covers VAL-02
- [ ] `tests/test_pipeline/test_dedup.py` -- covers VAL-03
- [ ] `tests/test_pipeline/test_report.py` -- covers VAL-05, OUT-03
- [ ] `tests/test_export/test_csv.py` -- covers VAL-06, OUT-01
- [ ] `tests/test_export/test_json.py` -- covers OUT-02
- [ ] Framework install: `pip install pytest` -- no test infra exists yet

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/daviddrysdale_github_io_python-phonenumbers` -- parse, format, validate, E.164, region handling
- Context7 `/pydantic/pydantic` -- model_dump, computed_field, optional fields, serialization
- Context7 `/pytest-dev/pytest` -- parametrize, fixtures, tmp_path, conftest
- Python stdlib docs -- csv, json, html, urllib.parse, re, unicodedata

### Secondary (MEDIUM confidence)
- Web search on UTF-8 BOM CSV for Excel -- confirmed `utf-8-sig` encoding approach, `newline=''` requirement

### Tertiary (LOW confidence)
- None -- all findings verified against primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- phonenumbers and pydantic are well-documented, stable libraries verified via Context7
- Architecture: HIGH -- composable pipeline pattern is standard for data processing; all stdlib functions verified
- Pitfalls: HIGH -- each pitfall is documented in official sources or verified through multiple references

**Research date:** 2026-03-13
**Valid until:** 2026-04-12 (30 days -- stable domain, no fast-moving dependencies)
