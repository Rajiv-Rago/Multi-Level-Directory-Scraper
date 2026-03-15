# Multi-Level Directory Scraper

[![PyPI](https://img.shields.io/pypi/v/multi-level-directory-scraper)](https://pypi.org/project/multi-level-directory-scraper/)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
[![codecov](https://codecov.io/gh/Rajiv-Rago/Multi-Level-Directory-Scraper/graph/badge.svg)](https://codecov.io/gh/Rajiv-Rago/Multi-Level-Directory-Scraper)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A config-driven scraper that navigates hierarchical business directories (regions -> categories -> detail pages), handles JavaScript-rendered content via Playwright, and outputs clean, validated datasets in CSV and JSON.

## Problem

Business directory websites organize listings behind multiple navigation levels -- click a region, then a category, then individual listings. The data lives across hundreds of pages, many requiring JavaScript to render. Extracting it means:

- Traversing 3+ depth levels with different selectors at each level
- Rendering JS-heavy pages that static HTTP requests can't handle
- Handling pagination (next buttons, load-more, infinite scroll)
- Normalizing messy real-world data (phone formats, relative URLs, HTML entities)
- Deduplicating records that appear under multiple categories
- Surviving network errors, rate limits, and mid-run interruptions

This scraper solves all of these in a single config-driven tool.

## Key Features

- **Config-driven** -- site-specific selectors and URL patterns in YAML, scraping engine is generic
- **Multi-level navigation** -- traverses region -> category -> listing -> detail page hierarchies
- **JS rendering** -- Playwright for dynamic content, static HTTP for simple pages
- **Pagination** -- next-button, load-more, and infinite-scroll strategies
- **Data validation** -- phone normalization, URL resolution, whitespace cleanup, HTML entity decoding
- **Deduplication** -- removes duplicate records by name + address fingerprint
- **Checkpoint/resume** -- saves state on Ctrl+C, resumes without re-scraping visited pages
- **Retry with backoff** -- exponential backoff on 429/5xx, configurable attempt limits
- **Structured logging** -- timestamped, field-rich logs via structlog
- **Dual output** -- flat CSV and nested JSON with region/category hierarchy

## Quick Start

```bash
# Install from PyPI
pip install multi-level-directory-scraper
playwright install chromium

# Run with your config
scraper config.yaml

# Validate selectors before a full crawl
scraper config.yaml --dry-run
```

Or install from source:

```bash
git clone https://github.com/Rajiv-Rago/Multi-Level-Directory-Scraper.git
cd Multi-Level-Directory-Scraper
uv sync
uv run playwright install chromium
```

## Architecture

The scraper processes sites through a level-based pipeline:

```
Config (YAML)
    |
    v
CLI (typer) --> Config Loader (pydantic)
    |
    v
Politeness Controller (robots.txt, delays)
    |
    v
Crawl Orchestrator (level-based BFS)
    |
    +---> URL Frontier (dedup, per-level queues)
    +---> Fetcher (httpx static / Playwright JS)
    +---> Extractor (BeautifulSoup field extraction)
    +---> Pagination Handler (next/load-more/scroll)
    |
    v
Data Quality Pipeline
    |
    +---> Cleaning (whitespace, HTML entities)
    +---> Phone Normalizer (phonenumbers lib)
    +---> URL Resolver (relative -> absolute)
    +---> Deduplicator (name+address fingerprint)
    |
    v
Export (CSV + JSON) + Validation Report
```

**Key design decisions:**
- **Playwright over Selenium** -- modern async API, auto-wait, faster execution
- **Config-driven** -- adding a new site means writing a YAML file, not code
- **BeautifulSoup for parsing** -- Playwright renders the page, BS4 parses the HTML (fast, well-tested)
- **Level-based BFS** -- processes all URLs at depth N before moving to depth N+1, natural for directory hierarchies

## Data Quality

The validation pipeline normalizes and cleans every record:

| Step | What it does | Example |
|------|-------------|---------|
| Whitespace cleanup | Strips leading/trailing, collapses internal | `"  Acme  Corp  "` -> `"Acme Corp"` |
| HTML entity decoding | Converts entities to characters | `"O&#39;Brien"` -> `"O'Brien"` |
| Phone normalization | Standardizes to consistent format | `"2065550142"` -> `"(206) 555-0142"` |
| URL resolution | Converts relative to absolute | `"/about"` -> `"https://example.com/about"` |
| Deduplication | Removes duplicates by name+address | 263 records -> 247 unique |

Sample validation report:

```
═══════════════════════════════════════════════════════
  Data Quality Report
═══════════════════════════════════════════════════════
  Records:      263 total, 247 unique, 16 duplicates removed
  Completeness: 94.2% field completeness
  Phones:       231 normalized, 4 failed
  URLs:         218 resolved, 2 invalid
  Warnings:     6 total
  Duration:     342.18s
═══════════════════════════════════════════════════════
```

## Resilience

The scraper handles real-world failure modes without losing work.

**HTTP retry with exponential backoff** -- recovers from rate limits and server errors:

```
2026-03-13 08:17:12 [warning  ] http_error                 url=...mountain-west/technology status=429
2026-03-13 08:17:12 [info     ] retry_backoff              attempt=1/3 wait=4.2s reason=rate_limited
2026-03-13 08:17:16 [info     ] fetch                      url=...mountain-west/technology depth=2 renderer=playwright
2026-03-13 08:17:19 [info     ] record_extracted           name=Summit Cloud Services
```

**Checkpoint save on Ctrl+C** -- first signal saves state gracefully:

```
^C
2026-03-13 08:20:03 [info     ] Received signal SIGINT, finishing current page and saving state...
2026-03-13 08:20:03 [info     ] Checkpoint saved: 187 pages visited, 125 pending
2026-03-13 08:20:03 [info     ] State saved: 187 pages visited, 125 pending, 156 records
2026-03-13 08:20:03 [info     ] Partial results saved to output/partial_results.csv
```

**Resume from checkpoint** -- picks up where it left off, skipping visited pages:

```
$ python -m scraper config.yaml --resume
2026-03-13 08:25:10 [info     ] config_loaded              site=US Business Directory levels=3
2026-03-13 08:25:10 [info     ] checkpoint_resumed         visited=187 pending=125
2026-03-13 08:25:10 [info     ] Resuming crawl: skipping 187 already-visited pages
2026-03-13 08:25:11 [info     ] fetch                      url=...great-lakes/manufacturing depth=2 renderer=static
...
2026-03-13 08:31:22 [info     ] crawl_complete             total_records=247 total_urls=312
2026-03-13 08:31:22 [info     ] Checkpoint file cleaned up
```

A second Ctrl+C triggers an emergency save and immediate exit -- the scraper never loses data silently.

## Sample Output

**CSV** (first 5 rows):

| region | category | name | address | phone | website |
|--------|----------|------|---------|-------|---------|
| Pacific Northwest | Technology | Cascade Software Solutions | 1200 Pine St, Seattle, WA 98101 | (206) 555-0142 | cascadesoftware.example.com |
| Pacific Northwest | Technology | Emerald Data Systems | 834 Oak Ave, Portland, OR 97201 | (503) 555-0198 | emeralddata.example.com |
| Pacific Northwest | Healthcare | Rainier Medical Group | 2100 Cedar Blvd, Seattle, WA 98102 | (206) 555-0231 | rainiermedical.example.com |
| Mountain West | Technology | Summit Cloud Services | 450 Aspen Way, Denver, CO 80202 | (303) 555-0167 | summitcloud.example.com |
| Mountain West | Construction | Alpine Builders LLC | 789 Spruce Dr, Salt Lake City, UT 84101 | (801) 555-0284 | |

**JSON** (nested by region/category):

```json
{
  "regions": {
    "Pacific Northwest": {
      "Technology": [
        {
          "name": "Cascade Software Solutions",
          "address": "1200 Pine St, Seattle, WA 98101",
          "phone": "(206) 555-0142",
          "website": "https://cascadesoftware.example.com",
          "description": "Full-stack development and cloud consulting"
        }
      ]
    }
  }
}
```

Full sample files: [`docs/samples/`](docs/samples/)

## Configuration

Site-specific settings live in a YAML config file:

```yaml
site:
  name: "US Business Directory"
  base_url: "https://directory.example.com"
  output_dir: "./output"
  request_delay:
    min: 1.0    # Minimum seconds between requests
    max: 3.0    # Maximum seconds (randomized)
  max_pages: 500  # Safety limit per level
  log_level: "info"

levels:
  - name: "regions"
    depth: 0
    link_selector: "a.region-link"
    fields:
      - name: "region_name"
        selector: "h2.title"
      - name: "region_url"
        selector: "a.region-link"
        attribute: "href"

  - name: "categories"
    depth: 1
    link_selector: "a.category-link"
    pagination:
      type: "next_button"
      selector: "a.next-page"
    fields:
      - name: "category_name"
        selector: "h3.category"

  - name: "listings"
    depth: 2
    link_selector: "a.listing-link"
    fields:
      - name: "name"
        selector: "h1.business-name"
      - name: "address"
        selector: "span.address"
      - name: "phone"
        selector: "span.phone"
      - name: "website"
        selector: "a.website"
        attribute: "href"
      - name: "description"
        selector: "div.description"
```

## Setup

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/) (recommended) or pip

```bash
# 1. Clone
git clone https://github.com/Rajiv-Rago/Multi-Level-Directory-Scraper.git
cd Multi-Level-Directory-Scraper

# 2. Install (pick one)
uv sync                    # recommended
pip install -e .           # fallback

# 3. Install browser
uv run playwright install chromium

# 4. Verify
uv run python -m scraper --help

# 5. Dry-run (validate selectors without full crawl)
uv run python -m scraper config.yaml --dry-run

# 6. Full crawl
uv run python -m scraper config.yaml

# 7. Resume interrupted crawl
uv run python -m scraper config.yaml --resume
```

**CLI options:**

| Flag | Description |
|------|------------|
| `--dry-run` | Validate config and test selectors on level-0 page |
| `--resume` | Resume from checkpoint if available |
| `--force` | Force resume even with config mismatch |
| `--output-dir DIR` | Override output directory |
| `--delay-min N` | Override minimum request delay (seconds) |
| `--delay-max N` | Override maximum request delay (seconds) |
| `--max-pages N` | Override maximum pages per level |
| `--log-level LEVEL` | Set log level: debug/info/warning |

**Running tests:**

```bash
uv sync --dev
uv run pytest
```

## Project Structure

```
src/scraper/          # Core scraping engine
  cli.py              # CLI entry point (typer)
  config.py           # YAML config loading (pydantic)
  orchestrator.py     # Level-based BFS crawl
  frontier.py         # URL queue with dedup
  fetcher.py          # Static (httpx) + JS (Playwright) fetching
  extractor.py        # BeautifulSoup field extraction
  pagination.py       # Next-button, load-more, infinite scroll
  retry.py            # Exponential backoff (tenacity)
  politeness.py       # robots.txt + request delays
  checkpoint.py       # Atomic checkpoint save/load
  signals.py          # SIGINT/SIGTERM cooperative shutdown
  logging.py          # Structured logging (structlog)

src/pipeline/         # Data quality pipeline
  cleaning.py         # Whitespace + HTML entity cleanup
  phone.py            # Phone number normalization
  urls.py             # URL resolution
  dedup.py            # Record deduplication

src/export/           # Output writers
  csv_export.py       # Flat CSV export
  json_export.py      # Nested JSON export
  report.py           # Validation report

tests/                # 195+ tests (pytest)
```

## License

MIT
