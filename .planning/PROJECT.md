# Multi-Level Directory Scraper

## What This Is

A config-driven scraper that navigates multi-level business directories (regions → listings → detail pages), handles JavaScript-rendered content via browser automation, and outputs clean, validated datasets in CSV and JSON formats. Designed as a portfolio project demonstrating web scraping, data quality, and resilience engineering.

## Core Value

Reliably extract structured data from a hierarchical, JS-rendered directory site — traversing all levels, handling dynamic content, and producing validated output that opens cleanly in any spreadsheet tool.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-level navigation (3+ depth levels: regions → listings → detail pages)
- [ ] JS-rendered content handling via browser automation (Playwright)
- [ ] Configurable field extraction with null handling for missing fields
- [ ] Hierarchical relationship preservation (region/category per record)
- [ ] Pagination handling (next page, load more, infinite scroll)
- [ ] URL deduplication within a run
- [ ] Data validation: phone normalization, URL validation, whitespace stripping, HTML entity decoding
- [ ] Record deduplication by unique identifier (name + address or URL)
- [ ] CSV output with correct encoding and headers
- [ ] JSON output with nested region/category structure
- [ ] Validation report (total records, completeness, duplicates, errors, duration)
- [ ] Resilience: exponential backoff on 429, retry on 5xx, robots.txt respect
- [ ] Configurable request delays (default 1-3s randomized)
- [ ] Partial result persistence on interruption
- [ ] Structured logging with timestamps, URLs, and error types
- [ ] Config file (YAML/JSON) for site-specific settings (selectors, URL patterns, fields)
- [ ] CLI argument overrides for one-off runs
- [ ] Portfolio-quality README documenting problem, approach, data quality, resilience, and sample output

### Out of Scope

- Login-protected content — adds auth complexity, not needed for portfolio demo
- CAPTCHA bypassing — ethical and legal concerns
- Real-time monitoring / continuous scraping — this is a batch tool
- Database storage — CSV/JSON output sufficient for portfolio demonstration
- Mobile app or web UI — CLI tool only

## Context

- Portfolio project showcasing web scraping, data engineering, and resilience skills
- Target site will be chosen during development — must be publicly accessible, JS-rendered, with 3+ navigation levels
- Architecture is config-driven: site-specific selectors and URL patterns live in configuration, scraping engine is generic
- Yellow Pages-style directories, chamber of commerce listings, or industry-specific directories are likely targets

## Constraints

- **Tech stack**: Python 3.10+ with Playwright, BeautifulSoup4, pandas, httpx — per spec suggestions
- **Ethics**: Must respect robots.txt, use polite delays, no aggressive crawling
- **Output**: CSV must open cleanly in Excel/Google Sheets; JSON must pass schema validation
- **Resilience**: Must handle 404, 429, 5xx, timeouts, and mid-run interruption gracefully

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Config-driven architecture | Generic engine + site-specific config shows better design sense than hardcoded scraper | — Pending |
| YAML/JSON config with CLI overrides | Config file for defaults, CLI for one-off overrides — standard pattern | — Pending |
| Playwright over Selenium | Modern, faster, better async support, auto-wait capabilities | — Pending |
| Pick target site during build | Design generic first, validate against real site when building | — Pending |

---
*Last updated: 2026-03-13 after initialization*
