# Requirements: Multi-Level Directory Scraper

**Defined:** 2026-03-13
**Core Value:** Reliably extract structured data from a hierarchical, JS-rendered directory site — traversing all levels, handling dynamic content, and producing validated output.

## v1 Requirements

### Navigation

- [ ] **NAV-01**: Given a directory homepage, the scraper discovers and follows all region/category links to produce a complete list of second-level pages
- [ ] **NAV-02**: Given a second-level listing page, the scraper discovers and follows all individual entity links (e.g., company profile pages)
- [ ] **NAV-03**: Given a paginated listing, the scraper follows all pagination controls (next page, load more, infinite scroll) until no more results are available
- [ ] **NAV-04**: The scraper never visits the same URL twice within a single run
- [ ] **NAV-05**: If a navigation link returns a 404 or timeout, the scraper logs the failure and continues without crashing

### JS Rendering

- [ ] **JS-01**: Given a page where content loads via JavaScript, the scraper waits until target data elements are present in the DOM before extraction
- [ ] **JS-02**: Given a page with infinite scroll, the scraper triggers scroll events until all items are loaded or a configurable maximum is reached
- [ ] **JS-03**: If JS content fails to render within a configurable timeout (default 15s), the scraper logs a warning with the URL and moves on

### Extraction

- [ ] **EXT-01**: For each entity, the scraper extracts all fields specified in the config (name, address, phone, website, category, description, and any custom fields)
- [ ] **EXT-02**: If a field is missing from a page, the scraper records it as null/empty rather than skipping the entire record
- [ ] **EXT-03**: Each record includes the region and category it was found under (hierarchical context preserved)
- [ ] **EXT-04**: Given a page with multiple HTML structures (e.g., archived vs current format), the scraper handles both via multiple selector fallback per field
- [ ] **EXT-05**: Each field in config supports a priority list of CSS selectors; the scraper tries them in order and uses the first match

### Data Quality

- [ ] **VAL-01**: Phone numbers are normalized to a consistent format (E.164 or local standard)
- [ ] **VAL-02**: URLs are validated as well-formed; relative URLs are resolved to absolute
- [ ] **VAL-03**: Duplicate records (same entity in multiple categories) are flagged and deduplicated by composite key (name + address, or URL)
- [ ] **VAL-04**: Leading/trailing whitespace is stripped from all text fields; HTML entities are decoded
- [ ] **VAL-05**: After extraction, a validation summary reports: total records, records with missing fields, duplicates found, extraction errors, and run duration
- [ ] **VAL-06**: The CSV output opens cleanly in Excel/Google Sheets with correct column headers and no encoding artifacts (UTF-8 BOM)

### Output

- [ ] **OUT-01**: The scraper produces a CSV file with columns: region, category, name, address, phone, website, description, source_url, scraped_at
- [ ] **OUT-02**: The scraper produces a JSON file with nested region/category structure
- [ ] **OUT-03**: The scraper produces a validation report file with summary statistics

### Resilience

- [ ] **RES-01**: On HTTP 429, the scraper backs off with exponential delay (starting at 5s, max 60s) and retries up to 3 times
- [ ] **RES-02**: On HTTP 5xx, the scraper retries once after 10s, then logs and skips
- [ ] **RES-03**: The scraper respects robots.txt directives for the target site
- [ ] **RES-04**: A configurable delay between requests (default 1-3s, randomized) prevents aggressive crawling
- [ ] **RES-05**: If interrupted mid-run, partial results already extracted are saved to disk
- [ ] **RES-06**: All errors and warnings are written to a log file with timestamps, URLs, and error types
- [ ] **RES-07**: The scraper saves crawl state (visited URLs, pending queue, current progress) periodically and on SIGINT/SIGTERM
- [ ] **RES-08**: On restart, the scraper detects a checkpoint file and offers to resume from last saved state

### Configuration & UX

- [ ] **CFG-01**: Site-specific settings (base URL, per-level selectors, pagination rules, field mappings) are defined in a YAML/JSON config file
- [ ] **CFG-02**: CLI arguments override config file values for one-off runs (output dir, delay, max pages, verbosity, dry-run)
- [ ] **CFG-03**: The config file is validated against a schema on load; clear error messages for invalid config
- [ ] **CFG-04**: Dry-run mode fetches one page per level, extracts fields, and prints results without full crawl or output files
- [ ] **CFG-05**: During crawl, terminal displays progress per level (pages scraped, error count, estimated time remaining)

### Documentation

- [ ] **DOC-01**: README documents: problem statement, approach and key decisions, data quality achieved, resilience with log examples, sample output, and setup instructions (runnable in under 5 minutes)

## v2 Requirements

### Enhanced Resilience

- **RES-V2-01**: Adaptive delay based on server response times (auto-throttle)

### Enhanced Output

- **OUT-V2-01**: NDJSON output (one record per line) for streaming pipelines

### Enhanced Config

- **CFG-V2-01**: Config inheritance (base config + site-specific overrides) for multi-site support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Login-protected content | Adds auth complexity, ethical/legal concerns, not needed for portfolio demo |
| CAPTCHA solving/bypass | Ethical gray area, signals wrong intent for portfolio work |
| Proxy rotation / IP management | Overkill for polite batch tool; signals aggressive crawling |
| Stealth / anti-detection | Arms race with anti-bot systems; portfolio should demonstrate ethical scraping |
| Real-time monitoring dashboard | Massive scope creep; terminal progress + logs achieve same goal |
| Database storage | CSV/JSON sufficient; database integration is a separate project |
| Distributed crawling | Different architecture entirely; single-machine handles directory scale |
| LLM-powered extraction | Non-deterministic, costly; CSS selectors work perfectly for structured directories |
| Scheduled/continuous scraping | Turns batch tool into a service; users can wrap in cron themselves |
| Mobile app or web UI | CLI tool only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 1 | Pending |
| CFG-02 | Phase 1 | Pending |
| CFG-03 | Phase 1 | Pending |
| CFG-04 | Phase 1 | Pending |
| CFG-05 | Phase 1 | Pending |
| RES-03 | Phase 1 | Pending |
| RES-04 | Phase 1 | Pending |
| RES-06 | Phase 1 | Pending |
| NAV-01 | Phase 2 | Pending |
| NAV-02 | Phase 2 | Pending |
| NAV-03 | Phase 2 | Pending |
| NAV-04 | Phase 2 | Pending |
| NAV-05 | Phase 2 | Pending |
| JS-01 | Phase 2 | Pending |
| JS-02 | Phase 2 | Pending |
| JS-03 | Phase 2 | Pending |
| EXT-01 | Phase 2 | Pending |
| EXT-02 | Phase 2 | Pending |
| EXT-03 | Phase 2 | Pending |
| EXT-04 | Phase 2 | Pending |
| EXT-05 | Phase 2 | Pending |
| RES-01 | Phase 2 | Pending |
| RES-02 | Phase 2 | Pending |
| VAL-01 | Phase 3 | Pending |
| VAL-02 | Phase 3 | Pending |
| VAL-03 | Phase 3 | Pending |
| VAL-04 | Phase 3 | Pending |
| VAL-05 | Phase 3 | Pending |
| VAL-06 | Phase 3 | Pending |
| OUT-01 | Phase 3 | Pending |
| OUT-02 | Phase 3 | Pending |
| OUT-03 | Phase 3 | Pending |
| RES-05 | Phase 4 | Pending |
| RES-07 | Phase 4 | Pending |
| RES-08 | Phase 4 | Pending |
| DOC-01 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after roadmap creation*
