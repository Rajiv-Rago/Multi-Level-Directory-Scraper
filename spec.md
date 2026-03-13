# Behavioral Spec: Multi-Level Directory Scraper

---

## 1. Problem Statement

Build a scraper that navigates a multi-level business directory (regions → companies → company details), extracts structured data from JavaScript-rendered pages, and delivers clean, validated output in CSV and JSON formats.

| Property | Detail |
|----------|--------|
| **Goal** | Reliably extract structured data from a hierarchical, JS-rendered directory site |
| **Target site** | A publicly accessible, JS-rendered business directory with at least 3 navigation levels |
| **Output** | Structured CSV + JSON datasets with validation report |
| **Not in scope** | Login-protected content, CAPTCHA bypassing, real-time monitoring, database storage |

---

## 2. Behavioral Specifications

Each behavior below describes what the system must do from the outside. Implementation details are deliberately omitted — this spec defines the "what," not the "how."

### 2.1 Multi-Level Navigation

**Context:** The scraper must traverse a hierarchical site structure with at least three depth levels.

1. **BEH-NAV-01:** Given a directory homepage, the scraper discovers and follows all region/category links to produce a complete list of second-level pages.
2. **BEH-NAV-02:** Given a second-level listing page, the scraper discovers and follows all individual entity links (e.g., company profile pages).
3. **BEH-NAV-03:** Given a paginated listing, the scraper follows all pagination controls (next page, load more, infinite scroll) until no more results are available.
4. **BEH-NAV-04:** The scraper never visits the same URL twice within a single run.
5. **BEH-NAV-05:** If a navigation link returns a 404 or timeout, the scraper logs the failure and continues to the next link without crashing.

### 2.2 Dynamic Content Handling

**Context:** Target pages use JavaScript to render content. The scraper must handle this reliably.

1. **BEH-JS-01:** Given a page where content loads via JavaScript (AJAX, client-side rendering), the scraper waits until the target data elements are present in the DOM before extraction.
2. **BEH-JS-02:** Given a page with infinite scroll, the scraper triggers scroll events until all items are loaded or a configurable maximum is reached.
3. **BEH-JS-03:** If JS content fails to render within a configurable timeout (default: 15 seconds), the scraper logs a warning with the URL and moves on.

### 2.3 Data Extraction

**Context:** Each entity page contains structured information that must be captured completely and accurately.

1. **BEH-EXT-01:** For each entity, the scraper extracts all specified fields (name, address, phone, website, category, description, and any other fields defined in the config).
2. **BEH-EXT-02:** If a field is missing from a page, the scraper records it as null/empty rather than skipping the entire record.
3. **BEH-EXT-03:** The scraper preserves the hierarchical relationship: each record includes the region and category it was found under.
4. **BEH-EXT-04:** Given a page with multiple HTML structures (e.g., archived vs. current format), the scraper handles both and produces consistent output.

### 2.4 Data Quality & Validation

**Context:** Output data must be clean, consistent, and verifiably correct.

1. **BEH-VAL-01:** Phone numbers are normalized to a consistent format (e.g., E.164 or local standard).
2. **BEH-VAL-02:** URLs are validated as well-formed. Relative URLs are resolved to absolute.
3. **BEH-VAL-03:** Duplicate records (same entity appearing in multiple categories) are flagged and deduplicated by a unique identifier (name + address, or URL).
4. **BEH-VAL-04:** Leading/trailing whitespace is stripped from all text fields. HTML entities are decoded.
5. **BEH-VAL-05:** After extraction, a validation summary is generated reporting: total records, records with missing fields, duplicates found, and any extraction errors.
6. **BEH-VAL-06:** The CSV output opens cleanly in Excel/Google Sheets with correct column headers and no encoding artifacts.

### 2.5 Resilience & Error Handling

**Context:** Scraping jobs must be robust against common failure modes.

1. **BEH-RES-01:** On HTTP 429 (rate limit), the scraper backs off with exponential delay (starting at 5s, max 60s) and retries up to 3 times.
2. **BEH-RES-02:** On HTTP 5xx, the scraper retries once after a 10-second wait, then logs and skips.
3. **BEH-RES-03:** The scraper respects robots.txt directives for the target site.
4. **BEH-RES-04:** A configurable delay between requests (default: 1–3 seconds, randomized) prevents aggressive crawling.
5. **BEH-RES-05:** If the scraper is interrupted mid-run, partial results already extracted are saved to disk (not lost).
6. **BEH-RES-06:** All errors and warnings are written to a log file with timestamps, URLs, and error types.

---

## 3. Output Specification

The scraper produces three output files per run:

| File | Description |
|------|-------------|
| **data.csv** | All extracted records in flat tabular format. Columns: region, category, name, address, phone, website, description, source_url, scraped_at |
| **data.json** | Same data in JSON array format with nested region/category structure |
| **validation_report.txt** | Summary statistics: total records, completeness per field, duplicates found, errors encountered, run duration |

---

## 4. Acceptance Criteria

The project is complete when all of the following are true:

- The scraper successfully navigates at least 3 levels deep on the target site
- JS-rendered content is captured (verifiable by comparing output against what a browser shows)
- Output CSV opens in Google Sheets with no formatting issues
- Output JSON is valid (passes a JSON schema validator)
- Validation report shows >95% field completeness on non-optional fields
- The scraper recovers gracefully from at least one simulated failure (e.g., timeout, 404)
- README documents: setup instructions, target site, approach taken, tools used, and sample output

---

## 5. Suggested Tech Stack

These are suggestions, not requirements. The spec is tool-agnostic.

| Component | Suggestion |
|-----------|------------|
| **Browser automation** | Playwright (preferred) or Selenium — needed for JS rendering |
| **HTML parsing** | BeautifulSoup4 — for extracting data from rendered DOM |
| **HTTP requests** | httpx or requests — for static pages or API endpoints if discovered |
| **Data processing** | pandas — for cleaning, deduplication, and CSV/JSON export |
| **Validation** | Custom Python script or pydantic models for schema validation |
| **Language** | Python 3.10+ |

---

## 6. README Must Include

Since this is a portfolio project, the README is as important as the code:

- **Problem:** What you scraped and why the site is non-trivial (JS rendering, multi-level, etc.)
- **Approach:** Key decisions you made (why Playwright over requests, how you handled pagination, etc.)
- **Data quality:** How you validated output and what completeness you achieved
- **Resilience:** How the scraper handles failures (with examples from logs)
- **Sample output:** A truncated sample of the CSV/JSON so reviewers can see the result without running it
- **Setup:** How to install and run in under 5 minutes