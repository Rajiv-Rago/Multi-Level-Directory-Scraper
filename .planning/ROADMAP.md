# Roadmap: Multi-Level Directory Scraper

## Overview

This project delivers a config-driven scraper that navigates hierarchical directory websites, extracts structured data from JS-rendered pages, and produces clean CSV/JSON output. The roadmap progresses from project skeleton and configuration (Phase 1), through the core crawl engine combining fetching, extraction, and multi-level navigation (Phase 2), into data quality and output formatting (Phase 3), and finishes with checkpoint/resume resilience and portfolio documentation (Phase 4). Each phase delivers a verifiable capability that the next phase builds on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Project skeleton with config loading, CLI, structured logging, and polite crawling basics
- [ ] **Phase 2: Crawl Engine** - Multi-level navigation with JS rendering, selector-based extraction, pagination, and HTTP resilience
- [ ] **Phase 3: Data Quality and Output** - Validation pipeline with phone/URL normalization, deduplication, and CSV/JSON export
- [ ] **Phase 4: Resilience and Documentation** - Checkpoint/resume on interruption and portfolio-quality README

## Phase Details

### Phase 1: Foundation
**Goal**: User can load a site config, run the CLI, and see validated settings with structured log output -- the scaffolding everything else plugs into
**Depends on**: Nothing (first phase)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, RES-03, RES-04, RES-06
**Success Criteria** (what must be TRUE):
  1. User can define a site config in YAML with base URL, per-level selectors, pagination rules, and field mappings, and the tool loads it without error
  2. User can override any config value via CLI arguments (output dir, delay, max pages, verbosity, dry-run)
  3. User receives a clear, specific error message when config is invalid (missing required fields, bad selector syntax, wrong types)
  4. User can run dry-run mode which fetches one page per level, extracts fields, and prints results to terminal without writing output files
  5. All operations produce structured log output with timestamps, URLs, and event types to both terminal and log file
**Plans**: 2 plans in 2 waves

Plans:
- [ ] 01-01: Project skeleton, config models, CLI, structured logging (Wave 1) [CFG-01, CFG-02, CFG-03, CFG-05, RES-06]
- [ ] 01-02: Politeness controller, dry-run mode (Wave 2) [RES-03, RES-04, CFG-04]

### Phase 2: Crawl Engine
**Goal**: User can point the tool at a real multi-level directory and get raw extracted records from all levels, with JS rendering, pagination, and retry handling
**Depends on**: Phase 1
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04, NAV-05, JS-01, JS-02, JS-03, EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, RES-01, RES-02
**Success Criteria** (what must be TRUE):
  1. Given a directory homepage, the scraper traverses all three levels (regions -> listings -> detail pages) and extracts records from every reachable entity page
  2. JS-rendered pages have their content fully loaded before extraction (no empty fields due to content not yet rendered)
  3. Paginated listings are followed to completion -- all pages of results are scraped, not just the first page
  4. Each extracted record carries its region and category context (hierarchical relationship preserved from parent pages)
  5. The same URL is never fetched twice in a run, and navigation failures (404, timeout) are logged and skipped without crashing
**Plans**: 3 plans, 2 waves

Plans:
- [ ] 02-01: URL Frontier + Dual-Mode Fetcher (Wave 1)
- [ ] 02-02: HTML Extractor + Retry Logic (Wave 1)
- [ ] 02-03: Pagination Handler + Crawl Orchestrator (Wave 2)

### Phase 3: Data Quality and Output
**Goal**: Raw extracted records are cleaned, validated, deduplicated, and exported as CSV and JSON files that open correctly in any tool
**Depends on**: Phase 2
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Phone numbers in output are normalized to a consistent format; URLs are validated and resolved to absolute; whitespace and HTML entities are cleaned
  2. Duplicate records (same entity appearing under multiple categories) are detected by composite key and deduplicated in the output
  3. CSV output opens cleanly in Excel and Google Sheets with correct column headers, UTF-8 encoding, and no artifacts
  4. JSON output preserves the hierarchical directory structure (records nested under region/category)
  5. A validation report is produced showing total records, records with missing fields, duplicates found, extraction errors, and run duration
**Plans**: 2 plans, 2 waves

Plans:
- [ ] 03-01: Pipeline core — pydantic models, text cleaning, phone normalization, URL validation, deduplication (Wave 1)
- [ ] 03-02: Export and reporting — CSV/JSON export, validation report, pipeline runner (Wave 2)

### Phase 4: Resilience and Documentation
**Goal**: The scraper survives interruptions without losing work, and the project is documented as a portfolio piece
**Depends on**: Phase 3
**Requirements**: RES-05, RES-07, RES-08, DOC-01
**Success Criteria** (what must be TRUE):
  1. If the scraper is interrupted mid-run (Ctrl+C or SIGTERM), all records extracted so far are saved to disk
  2. On restart after interruption, the scraper detects a checkpoint file and resumes from where it left off (no re-scraping of already-visited pages)
  3. README documents the problem, approach, data quality, resilience, sample output, and setup instructions such that a new user can run the tool in under 5 minutes
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Checkpoint/resume and signal handling (TDD)
- [ ] 04-02-PLAN.md — Portfolio-quality README documentation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planned | - |
| 2. Crawl Engine | 0/3 | Planned | - |
| 3. Data Quality and Output | 0/2 | Planned | - |
| 4. Resilience and Documentation | 0/2 | Planned | - |
