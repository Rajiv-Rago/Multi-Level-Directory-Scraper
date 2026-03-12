# Phase 3: Data Quality and Output - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Raw extracted records from Phase 2 are cleaned, validated, deduplicated, and exported as CSV and JSON files that open correctly in any tool. A validation report summarizes data quality. This phase does NOT modify the crawl engine or extraction logic -- it operates on already-extracted records as a post-processing pipeline.

</domain>

<decisions>
## Implementation Decisions

### Phone normalization
- Normalize to E.164 format (e.g., +14155551234)
- Assume a default country code from config (site-specific setting) for numbers without country prefix
- Numbers that cannot be parsed are kept as-is with a warning logged and counted in validation report
- Use the `phonenumbers` library (Google's libphonenumber port) -- the standard Python solution for this

### URL validation and resolution
- Relative URLs resolved to absolute using the source page URL as base
- Validated as well-formed (scheme + host at minimum)
- Invalid URLs kept in output but flagged in validation report (don't discard data)
- No HTTP HEAD check to verify URLs are live -- that would add network requests and slow the pipeline

### Text cleaning
- Strip leading/trailing whitespace from all text fields
- Decode HTML entities (e.g., `&amp;` -> `&`, `&#x27;` -> `'`)
- Collapse internal whitespace runs to single spaces (common in scraped HTML)
- Applied to every text field uniformly, before other validation steps

### Record deduplication
- Composite key: normalized(name) + normalized(address) as primary key
- Fallback: source_url if name+address is insufficient (e.g., missing address)
- Normalization for dedup: lowercase, strip whitespace, remove punctuation
- When duplicates found: keep the record with the most complete fields (fewest nulls)
- Duplicates are logged with both records' source_urls for traceability
- Dedup runs after all validation/cleaning (so normalized values are compared, not raw)

### CSV export
- UTF-8 with BOM (ensures Excel opens it correctly without encoding dialog)
- Columns in order: region, category, name, address, phone, website, description, source_url, scraped_at
- Standard CSV quoting (RFC 4180) -- fields containing commas, quotes, or newlines are quoted
- One file per run: `data.csv` in the output directory

### JSON export
- Nested hierarchy: `{ regions: [{ name, categories: [{ name, records: [...] }] }] }`
- Each record contains all fields (same as CSV columns minus region/category which are structural)
- Pretty-printed with 2-space indent for readability
- One file per run: `data.json` in the output directory

### Validation report
- Plain text format (`validation_report.txt`) as specified in the behavioral spec
- Sections: run metadata (timestamp, duration, target site), total records, field completeness (per-field counts of null/empty), duplicates found and removed, extraction errors/warnings, phone normalization failures, invalid URLs
- Human-readable format -- not machine-parseable (this is for the portfolio reviewer to glance at)

### Pipeline architecture
- Post-processing pipeline that runs after all records are extracted
- Order: text cleaning -> phone normalization -> URL validation -> deduplication -> export (CSV + JSON) -> validation report
- Operates on the full record set in memory (directory-scale data fits in memory easily)
- Pipeline is a separate module from the crawl engine -- takes records in, writes files out

### Claude's Discretion
- Exact validation report formatting and section order
- Whether to use pandas DataFrames or plain dicts for the pipeline (pandas suggested in spec but dicts may be simpler)
- Internal module structure (single file vs split by concern)
- Specific error message wording in logs

</decisions>

<specifics>
## Specific Ideas

- CSV must open cleanly in both Excel and Google Sheets -- UTF-8 BOM is critical for Excel compatibility
- Validation report is portfolio-facing: a reviewer should see it and immediately understand data quality achieved
- The spec acceptance criteria requires ">95% field completeness on non-optional fields" -- the report should make this number obvious
- Phone normalization to E.164 requires knowing the default country for the target site -- this comes from the site config

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code exists yet -- project is in planning phase. Phase 3 will be built from scratch.

### Established Patterns
- Config-driven architecture (from Phase 1) -- default country code for phone normalization should be a config field
- Structured logging (from Phase 1) -- validation warnings should use the same logging system

### Integration Points
- Input: receives extracted records from Phase 2's crawl engine (list of dicts or similar)
- Output: writes data.csv, data.json, validation_report.txt to configured output directory
- Config: reads site-specific settings (default country code, output directory) from the YAML config established in Phase 1

</code_context>

<deferred>
## Deferred Ideas

- NDJSON output for streaming pipelines -- listed as v2 requirement (OUT-V2-01), not in Phase 3 scope
- Database storage -- explicitly out of scope per PROJECT.md
- JSON schema validation of output -- could be useful but not required; reviewer can validate manually

</deferred>

---

*Phase: 03-data-quality-and-output*
*Context gathered: 2026-03-13*
