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
- Default country code is a required field in site config -- no guessing
- Numbers that cannot be parsed are kept as-is with a warning logged and counted in validation report (never discard data)
- Use `phonenumbers` library (Google's libphonenumber port) -- industry standard, impressive on a resume

### URL validation and resolution
- Relative URLs resolved to absolute using the source page URL as base
- Validated as well-formed (scheme + host at minimum)
- Invalid URLs kept in output but flagged in validation report (never discard data)
- No HTTP HEAD check -- out of scope, would add latency and network load

### Text cleaning
- Strip leading/trailing whitespace from all text fields
- Decode HTML entities (`&amp;` -> `&`, `&#x27;` -> `'`, etc.)
- Collapse internal whitespace runs to single spaces (common in scraped HTML)
- Applied uniformly to every text field, before other validation steps

### Record deduplication
- Composite key: normalized(name) + normalized(address) as primary
- Fallback: source_url when address is missing
- Normalization for dedup: lowercase, strip whitespace, remove punctuation
- When duplicates found: keep the record with the most complete fields (fewest nulls)
- Log every dedup decision with both records' source_urls for traceability
- Dedup runs after all cleaning/normalization (compare clean values, not raw)

### CSV export
- UTF-8 with BOM -- required for Excel to open without encoding prompts
- Columns in order: region, category, name, address, phone, website, description, source_url, scraped_at
- RFC 4180 quoting
- Output file: `data.csv` in configured output directory

### JSON export
- Nested hierarchy: `{ metadata: {...}, regions: [{ name, categories: [{ name, records: [...] }] }] }`
- Top-level `metadata` object includes: scraped_at timestamp, target site URL, total record count, schema version
- Each record contains all entity fields (region/category are structural, not repeated per record)
- Pretty-printed with 2-space indent
- Output file: `data.json` in configured output directory

### Validation report
- **JSON format** (`validation_report.json`), not plain text -- machine-readable reports are more impressive for a portfolio piece and demonstrate data engineering rigor
- Sections: run metadata (timestamp, duration, config used), record counts (total, unique, duplicates removed), field completeness (per-field: count present, count missing, percentage), normalization stats (phones normalized, phones failed, URLs resolved, URLs invalid), warnings list (each with field, value, reason, source_url)
- Also print a human-readable summary to stdout at end of run so the terminal shows key metrics
- The ">95% field completeness" acceptance criteria number should be front and center in both the JSON report and terminal summary

### Pipeline architecture
- Post-processing pipeline, separate module from crawl engine
- Order: text cleaning -> phone normalization -> URL validation -> deduplication -> export (CSV + JSON + report)
- Use pydantic models to define the record schema -- validates structure, provides serialization, and looks professional in the codebase
- Each pipeline stage is a function that takes records in, returns records out (composable, testable)
- Validation issues accumulate in a report collector passed through the pipeline, not scattered across log files
- Operates on full record set in memory (directory-scale data fits easily)

</decisions>

<specifics>
## Specific Ideas

- Portfolio reviewer should be able to open `validation_report.json` and immediately see data quality metrics -- this is the "proof of work" for the project
- Terminal summary after a run should look polished: record counts, completeness percentage, duplicate count, duration -- similar to how pytest prints a summary line
- The pydantic model for records doubles as documentation of the data schema -- a reviewer reading the code sees exactly what fields exist and their types
- JSON output with a `metadata` top-level key shows the output is self-describing, not just a raw data dump

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code exists yet -- project is in planning phase

### Established Patterns
- Config-driven architecture (Phase 1) -- default country code for phone normalization goes in site config
- Structured logging (Phase 1) -- validation warnings use the same logging system
- Python 3.10+ -- can use match statements, modern type hints, dataclasses/pydantic

### Integration Points
- Input: receives extracted records from Phase 2's crawl engine (list of dicts or pydantic models)
- Output: writes data.csv, data.json, validation_report.json to configured output directory
- Config: reads site-specific settings (default country code, output directory) from Phase 1 YAML config
- Stdout: prints human-readable summary at end of pipeline run

</code_context>

<deferred>
## Deferred Ideas

- NDJSON output for streaming pipelines -- listed as v2 requirement (OUT-V2-01)
- Database storage -- explicitly out of scope per PROJECT.md
- JSON schema validation of output files -- could auto-generate from pydantic models in a future phase

</deferred>

---

*Phase: 03-data-quality-and-output*
*Context gathered: 2026-03-13*
