# Project Research Summary

**Project:** Multi-Level Directory Scraper
**Domain:** Config-driven, hierarchical web directory scraper with JS rendering
**Researched:** 2026-03-13
**Confidence:** HIGH

## Executive Summary

This is a config-driven web scraping tool that navigates multi-level directory websites (regions -> listings -> detail pages), extracts structured business data using CSS/XPath selectors defined in YAML config files, and outputs clean CSV/JSON. The expert approach is well-established: Playwright for JS rendering, BeautifulSoup for HTML parsing, a level-based BFS crawl orchestrator, and a Scrapy-inspired data pipeline (clean -> validate -> dedup -> export). The YAML-driven architecture -- where adding a new target site requires zero Python code changes -- is the project's genuine differentiator over Scrapy/Crawlee/Crawl4AI, all of which require code-per-site.

The recommended stack is Python 3.12+ with Playwright (browser automation), BS4+lxml (parsing), httpx (HTTP), Pydantic (validation), pandas (export), and Typer (CLI). Every library choice has HIGH confidence based on ecosystem maturity and fit. The architecture follows a clear layered design: CLI -> Config -> Orchestrator -> Fetcher -> Extractor -> Pipeline -> Output, with each layer mapping to a single Python module. This is a mid-complexity project that benefits from a flat package structure, not a framework.

The primary risks are: (1) silent selector breakage producing empty data with no errors, (2) Playwright memory accumulation crashing long crawls, and (3) losing hierarchical context (which region a business belongs to) across navigation levels. All three are preventable with upfront architectural decisions -- field validation in the extraction layer, browser context rotation, and self-contained crawl tasks that carry parent metadata. The checkpoint/resume system is the highest-complexity differentiator feature and should be built after the core crawl loop is proven.

## Key Findings

### Recommended Stack

The stack is Python-centric with high-quality, well-maintained libraries for each concern. All core dependencies have HIGH confidence ratings. The key architectural insight from stack research is the clean handoff between layers: Playwright renders and returns HTML, BS4+lxml parses it locally (faster than crossing the Playwright bridge per-element), Pydantic validates at record construction time, and pandas exports.

**Core technologies:**
- **Python 3.12+**: Runtime -- mature async/await, type hints, scraping ecosystem dominance
- **Playwright 1.58+**: JS rendering -- auto-wait eliminates manual sleep/polling, native async API
- **BS4 + lxml**: HTML parsing -- forgiving parser with 5-10x speed from lxml backend; bulk extraction faster than Playwright's bridge
- **httpx 0.28+**: HTTP client -- async/sync dual API, integrates with Playwright's event loop (unlike requests)
- **Pydantic 2.12+**: Validation -- declarative field validators for phone/URL/whitespace, Rust core, JSON Schema output
- **pandas 3.0+**: Export -- DataFrame dedup, CSV with encoding control, JSON with orient options
- **phonenumbers**: Phone normalization -- Google libphonenumber port, E.164 formatting
- **Typer**: CLI -- type-hint-driven, auto-help, cleaner than Click/argparse for portfolio code
- **tenacity**: Retry -- decorator-based exponential backoff, keeps retry logic out of business logic
- **structlog**: Logging -- bound context (URL + depth) flows through all log calls, JSON + pretty output
- **PyYAML**: Config -- read-only YAML loading, simpler than ruamel.yaml for this use case

**Critical version requirements:** Python >=3.12 (performance, error messages, library compat). Playwright >=1.58 (latest auto-wait improvements). pandas >=3.0 (PyArrow-backed strings for better Unicode).

### Expected Features

**Must have (table stakes -- P1):**
- Multi-level navigation (3 depth levels) -- the defining feature
- Config-driven site definitions (YAML) -- architectural foundation
- JS-rendered content via Playwright -- 94% of modern directories need it
- CSS/XPath selector-based extraction -- universal extraction mechanism
- Pagination handling (next-page links minimum) -- directories always paginate
- URL deduplication -- prevents infinite loops in cross-linked categories
- Retry with exponential backoff + HTTP error handling (429/5xx/404)
- robots.txt compliance + configurable request delays -- ethical baseline
- CSV output with proper encoding (UTF-8 BOM) -- universal format
- Basic data cleaning (whitespace, HTML entities) -- minimum data quality
- Structured logging + CLI interface -- debuggability and usability

**Should have (differentiators -- P2):**
- Checkpoint/resume on interruption -- HIGH complexity, HIGH value for portfolio
- Validation report with quality metrics -- shows data engineering maturity
- Record deduplication by composite key -- catches cross-category duplicates
- JSON output with hierarchical structure -- preserves directory relationships
- Data validation pipeline (phone/URL normalization via Pydantic)
- Dry-run/preview mode -- config development UX
- Progress reporting (rich/tqdm) -- polish
- Schema validation of config files -- fail-fast on bad config

**Defer (v2+):**
- Multiple selector fallback per field -- adds config complexity
- Adaptive delay (auto-throttle) -- requires response time tracking
- NDJSON output -- niche use case

**Anti-features (explicitly exclude):**
- CAPTCHA solving, login/auth, proxy rotation, stealth/anti-detection -- wrong signals for portfolio
- Web UI dashboard, database storage, distributed crawling -- scope creep
- LLM-powered extraction -- overkill when CSS selectors work deterministically

### Architecture Approach

The architecture follows a layered, pipeline-based design inspired by Scrapy's component model but simplified for a single-purpose tool. Six layers with clean boundaries: CLI/Config (input), Crawl Orchestrator (coordination), Fetcher (HTTP/browser), Extractor (parsing), Data Pipeline (quality), and Output (export). The orchestrator uses level-based BFS -- processing all URLs at one depth before advancing to the next -- which is simpler to checkpoint, avoids crawler traps, and matches the natural directory hierarchy.

**Major components:**
1. **Config Loader** -- parse YAML, merge CLI overrides, validate schema with Pydantic
2. **Crawl Orchestrator** -- level-based traversal loop; the "brain" that coordinates all components
3. **URL Frontier** -- per-level URL queue + visited-URL dedup set
4. **Politeness Controller** -- robots.txt, configurable delays, backoff on 429/5xx
5. **Dual-Mode Fetcher** -- Playwright for JS pages, httpx for static; both return raw HTML via shared Protocol
6. **Selector-Driven Extractor** -- applies config selectors to BS4-parsed HTML; generic, never contains literal selectors
7. **Data Pipeline** -- clean -> validate -> dedup stages (Scrapy Item Pipeline pattern)
8. **Output Layer** -- CSV writer (UTF-8 BOM), JSON writer (nested), validation report
9. **Checkpoint/State Manager** -- persist crawl progress to JSON; enable resume on interruption

**Key patterns:** Config-driven selector mapping (zero code per site), dual-mode fetcher (Protocol interface), pipeline-stage processing (independently testable stages), self-contained crawl tasks (URL + parent context, no shared mutable state).

### Critical Pitfalls

1. **Silent selector breakage** -- Selectors stop matching after site layout changes, producing empty data with zero errors. Prevent by validating extraction results per-page (if all fields null on a successful page load, that is a selector failure, not an empty result). Implement a canary check before full runs.

2. **Playwright memory accumulation** -- BrowserContext accumulates ChannelOwner instances that are only flushed on context close. Long crawls leak memory until OOM. Prevent by rotating browser contexts every 50-100 pages and always closing pages in try/finally blocks.

3. **Lost hierarchical context** -- Detail page records lose which region/category they belong to. Prevent by designing crawl tasks as self-contained (url, parent_context) tuples from day one. Never rely on mutable shared state to track "current region."

4. **Unreliable page-ready detection** -- `networkidle` breaks on pages with analytics/websockets. `sleep()` is unreliable. Prevent by using `wait_for_selector()` targeting the specific content container needed, configurable per-level in YAML.

5. **CSV output breaking in Excel** -- Missing UTF-8 BOM, formula injection from `=+@-` prefixed cells, embedded newlines. Prevent by using `utf-8-sig` encoding and sanitizing cell values on export.

## Implications for Roadmap

Based on combined research, six phases ordered by dependency chain and risk reduction.

### Phase 1: Foundation
**Rationale:** Everything depends on config loading and CLI. These are zero-dependency components that establish the project skeleton and validate the YAML config schema -- catching problems before any crawling begins.
**Delivers:** Working CLI that loads and validates YAML config, structured logging setup, project structure with pyproject.toml and test scaffolding.
**Addresses:** Config-driven site definitions, CLI interface, structured logging, config schema validation.
**Avoids:** Config validation gaps (pitfall: mid-crawl crash from bad config).

### Phase 2: Fetch and Extract
**Rationale:** With config loading in place, the next dependency is the ability to fetch a page and extract data using config-defined selectors. This is the core technical risk -- Playwright integration, wait strategies, and the extraction pipeline must work reliably before building the crawl loop on top.
**Delivers:** Playwright fetcher that renders a JS page and returns HTML. BS4 extractor that applies config selectors to produce a record dict. Politeness controller (robots.txt, delays). End-to-end proof: config -> fetch one page -> extract fields -> print to stdout.
**Addresses:** JS-rendered content handling, CSS/XPath extraction, robots.txt compliance, configurable request delays.
**Avoids:** Unreliable page-ready detection (use wait_for_selector from the start), Playwright memory issues (establish page lifecycle patterns early), silent selector breakage (validate extraction results immediately).

### Phase 3: Crawl Loop
**Rationale:** With fetch+extract proven on single pages, the orchestrator wires them into a multi-level traversal. The URL frontier, deduplication, and hierarchical context propagation are added here. This phase produces the first end-to-end crawl across all three directory levels.
**Delivers:** Level-based BFS orchestrator, URL frontier with dedup, pagination (next-page links), hierarchical context carried through crawl tasks. End-to-end: config -> crawl 3 levels -> extract records with region/category metadata.
**Addresses:** Multi-level navigation, pagination handling, URL deduplication, hierarchical relationship preservation.
**Avoids:** Lost hierarchical context (self-contained crawl tasks from the start), URL dedup failures (normalize before comparison), recursive crawling without depth bounds (level-based, not recursive).

### Phase 4: Data Quality Pipeline
**Rationale:** With raw records flowing from the crawl loop, this phase adds the Pydantic validation pipeline (clean -> validate -> dedup) and the output writers. This is where the tool graduates from "script that scrapes" to "tool that produces clean data."
**Delivers:** Pydantic record models with field validators (phone normalization, URL validation, whitespace stripping). Record deduplication by composite key. CSV writer with UTF-8 BOM and formula injection protection. JSON writer with nested hierarchy. Basic validation report.
**Addresses:** Data validation pipeline, record deduplication, CSV output (proper encoding), JSON output (hierarchical), validation report.
**Avoids:** CSV/Excel encoding issues (UTF-8 BOM from first write), formula injection (sanitize on export), silent data quality problems (validation at construction time).

### Phase 5: Resilience
**Rationale:** The highest-complexity differentiator feature. Checkpoint/resume requires the crawl loop and data pipeline to be stable first -- you need to know what state to persist. This phase also hardens error recovery and adds adaptive behavior.
**Delivers:** Checkpoint persistence (visited URLs, pending queue, partial results) to JSON. Graceful shutdown on SIGINT/SIGTERM. Resume from checkpoint on restart. Retry hardening (DNS failures, connection resets, SSL errors beyond just HTTP status codes).
**Addresses:** Checkpoint/resume on interruption, retry hardening.
**Avoids:** Total data loss on crash (incremental state persistence), re-scraping already-visited pages (persisted visited set).

### Phase 6: Polish
**Rationale:** With the tool functionally complete, this phase adds UX polish and optimizations that elevate it from working tool to portfolio piece.
**Delivers:** Progress reporting (rich/tqdm with per-level counts and ETA), dry-run/preview mode, httpx fetcher for static pages (optimization), browser context rotation for long crawls, comprehensive error messages (not tracebacks).
**Addresses:** Progress reporting, dry-run/preview mode, Playwright memory management at scale, UX polish.
**Avoids:** UX pitfalls (no progress indication, unhelpful error messages), Playwright memory accumulation on large crawls.

### Phase Ordering Rationale

- **Phases 1-3 form the critical path:** Config -> Fetch -> Crawl. Each phase enables the next. No parallelism possible here.
- **Phase 4 (Data Quality) before Phase 5 (Resilience):** Checkpointing requires knowing what a "clean record" looks like, since partial results must be valid. The pipeline must be stable before persisting its output.
- **Phase 6 (Polish) is deliberately last:** Context rotation, progress bars, and dry-run mode are valuable but not load-bearing. They build on a working system.
- **Pagination is split:** Basic next-page link following goes in Phase 3 (required for functional crawling). Click-to-load-more and infinite scroll can be added in Phase 6 (Playwright-specific pagination patterns).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Fetch and Extract):** Playwright wait strategies are site-specific. Research the actual target directory site's loading behavior. The `wait_for_selector` vs `networkidle` decision depends on the specific site.
- **Phase 5 (Resilience):** Checkpoint/resume has no single standard pattern for custom scrapers. Scrapy's JOBDIR and Crawlee's RequestQueue are references but need adaptation. The state serialization format and atomic write strategy need design work.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** PyYAML loading, Typer CLI, Pydantic config validation -- all thoroughly documented, no unknowns.
- **Phase 3 (Crawl Loop):** BFS level traversal is a well-understood pattern. URL frontier and dedup are textbook.
- **Phase 4 (Data Quality):** Pydantic validators, pandas CSV export, phonenumbers normalization -- all have extensive docs and examples.
- **Phase 6 (Polish):** rich/tqdm progress bars, dry-run mode -- straightforward implementations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every library verified at current stable versions via PyPI. Well-established ecosystem with no controversial choices. |
| Features | HIGH | Feature landscape validated against Scrapy, Crawlee, Crawl4AI, and Scrapling. Clear MVP vs differentiator separation. |
| Architecture | HIGH | Level-based BFS, config-driven selectors, pipeline processing are all established patterns from the Scrapy ecosystem. |
| Pitfalls | HIGH | Playwright memory issues verified against actual GitHub issues. Selector fragility and CSV encoding are well-documented community knowledge. |

**Overall confidence:** HIGH

### Gaps to Address

- **Target site specifics:** Research was domain-general. The actual target directory site's loading behavior, pagination pattern, and DOM structure will need investigation during Phase 2. A spike/prototype against the real site is recommended.
- **robots.txt edge cases:** urllib.robotparser handles basic Disallow but does not implement RFC 9309 (2022). If the target site uses Crawl-delay directives, consider `protego` as a drop-in replacement.
- **Concurrency model:** Research recommends single-threaded async as sufficient for the target scale (<1K pages). If the target directory is larger, asyncio.Semaphore-bounded concurrency (3-5 concurrent fetches) should be added in Phase 3 or 6.
- **Click-to-load-more pagination:** Phase 3 covers next-page link following. Playwright-specific pagination (clicking "Load More" buttons, infinite scroll) needs site-specific research during Phase 2 or 6 depending on the target site.
- **pandas 3.0 compatibility:** pandas 3.0 defaults to PyArrow-backed strings. Verify that CSV export with `utf-8-sig` works correctly. LOW risk but worth a quick test early.
- **Playwright context rotation interval:** Research identifies the need but not the optimal interval. Start with every 50 pages and adjust empirically.

## Sources

All sources documented in individual research files:
- [STACK.md](.planning/research/STACK.md) -- 15 sources (PyPI, official docs, comparison articles)
- [FEATURES.md](.planning/research/FEATURES.md) -- 14 sources (Scrapy, Crawlee, Crawl4AI, best practice guides)
- [ARCHITECTURE.md](.planning/research/ARCHITECTURE.md) -- 8 sources (Scrapy architecture, system design references)
- [PITFALLS.md](.planning/research/PITFALLS.md) -- 19 sources (GitHub issues, production scraping guides, encoding references)

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
