# Phase 2: Crawl Engine - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Point the tool at a real multi-level directory and get raw extracted records from all levels, with JS rendering, pagination, and retry handling. This phase builds the fetcher, extractor, URL frontier, pagination follower, and orchestrator that ties them together. Data validation/cleaning and output formatting are Phase 3. Checkpoint/resume is Phase 4.

Requirements in scope: NAV-01 through NAV-05, JS-01 through JS-03, EXT-01 through EXT-05, RES-01, RES-02.

</domain>

<decisions>
## Implementation Decisions

### Target site strategy
- Do NOT hardcode to a specific site during engine development -- the tool is config-driven by design
- Build the engine against the config schema (selectors, levels, pagination rules defined in YAML)
- Use a real publicly accessible directory to validate the engine once built -- a chamber of commerce directory, industry listing, or Yellow Pages-style site with 3+ navigation levels and JS rendering
- The target site is chosen at integration testing time, not at architecture time -- this keeps the engine generic
- Create an example config YAML for a real site as the validation artifact

### Concurrency model
- Sequential async processing (one page at a time per level) for the initial build
- Polite delays of 1-3s between requests already dominate wall-clock time; parallelism adds complexity without meaningful speedup at directory scale (<1K pages)
- Architecture should not preclude future concurrency: fetcher interface is async, so adding a semaphore-bounded concurrency wrapper later is straightforward
- Single Playwright browser instance, single context, create/close individual Page objects per fetch (avoid the anti-pattern of launching browsers per page)

### Page readiness detection
- Primary strategy: Playwright `wait_for_selector` targeting the specific data element defined in config (per-level wait selector)
- Each level in the config specifies a `wait_selector` field -- the CSS selector that must be present before extraction begins
- Fallback: if no `wait_selector` is configured, default to `wait_for_load_state("networkidle")` with configurable timeout
- Timeout default: 15 seconds (per JS-03 requirement), configurable in site config
- On timeout: log warning with URL and move on (do not crash or retry -- the page may just be slow or broken)

### Extraction strictness
- Lenient by default: missing fields recorded as null, record still saved (per EXT-02 requirement)
- Never skip an entire record because one field is missing
- Track field extraction success/failure counts per level for the validation report (feeds Phase 3)
- Multiple selector fallback per field: config supports a priority list of CSS selectors per field (EXT-05); try in order, use first match
- Log which selector matched (debug level) for config tuning

### Pagination approach
- Config specifies pagination type per level: `next_page` (follow a link), `load_more` (click a button via Playwright), or `infinite_scroll` (scroll to load via Playwright)
- `next_page`: extract href from pagination selector, follow until selector not found
- `load_more`: click the selector via Playwright, wait for new content, repeat until selector disappears or max pages reached
- `infinite_scroll`: scroll to bottom via Playwright, wait for new items, repeat until no new items load or max items reached (per JS-02)
- Configurable max pages per level as a safety cap (prevents infinite pagination loops)

### URL frontier and deduplication
- In-memory set of visited URLs (sufficient for single-run batch tool at directory scale)
- Normalize URLs before comparison: strip trailing slashes, sort query parameters, lowercase scheme and host
- Per-level URL queue (deque) -- BFS within each level, levels processed sequentially
- Each URL in the frontier carries ancestor metadata (which parent pages led to it) for hierarchical context propagation (EXT-03)

### HTTP retry and resilience
- 429 responses: exponential backoff starting at 5s, max 60s, up to 3 retries (per RES-01)
- 5xx responses: single retry after 10s, then log and skip (per RES-02)
- 404 responses: log and skip, mark URL as visited (not an error -- listings get removed)
- Connection timeout: 30s for Playwright navigation, 15s for httpx requests
- Use tenacity decorators on the fetch function for clean separation of retry logic from business logic

### Fetcher architecture
- Dual-mode fetcher with shared interface (Protocol class with async `fetch(url) -> str`)
- Playwright fetcher for JS-rendered pages (default for most directory sites)
- httpx fetcher for static pages (optimization lever -- can be specified per-level in config)
- Config determines which fetcher per level via a `renderer` field: `"browser"` (default) or `"static"`
- Playwright fetcher: get full HTML via `page.content()`, then parse with BS4+lxml locally (faster than crossing the Python-to-browser bridge for each selector)

### Hierarchical context propagation
- Each URL in the frontier carries an `ancestors` list: metadata extracted from parent levels (region name, category name, parent URL)
- When extracting links from a non-detail page, the current page's identity (e.g., region name extracted from a heading selector) is appended to ancestors
- Detail page records include region and category fields populated from ancestor metadata
- Config specifies a `context_selector` per non-detail level to extract the identity label for that level

### Claude's Discretion
- Internal data structures for the URL frontier (deque, dataclass, namedtuple -- whatever is cleanest)
- Exact Playwright page lifecycle (when to create/close pages within the fetch call)
- How to structure the orchestrator's main loop (async generator, simple async for, etc.)
- Logging verbosity levels and format details
- Whether to use a Protocol class or ABC for the fetcher interface
- URL normalization implementation details

</decisions>

<specifics>
## Specific Ideas

- Architecture research recommends the Scrapy-inspired pattern: Orchestrator drives level-based traversal, Frontier manages URLs, Fetcher handles rendering, Extractor applies selectors
- The `page.content()` -> BS4 handoff pattern is preferred over Playwright's built-in `query_selector_all` for bulk extraction (avoids repeated Python-to-browser bridge crossings)
- Config example from architecture research shows the target YAML structure: `levels` array with `depth`, `name`, `link_selector`, `url_pattern`, `pagination`, `fields`, and `is_detail_page` keys
- Stack research specifically notes: "tenacity wraps Playwright calls -- @retry decorator on the page-fetching function, not on individual selectors"
- Browser reuse pattern: one browser for entire crawl session, one context, individual pages created/closed per fetch

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code exists yet -- Phase 1 (Foundation) has not been built
- Phase 2 depends on Phase 1 delivering: config loader, CLI skeleton, structured logging, politeness basics (robots.txt, delays)

### Established Patterns
- No established patterns yet -- this phase will establish the core crawling patterns
- Architecture research provides the reference patterns: level-based orchestration, config-driven selectors, dual-mode fetcher, pipeline-stage processing

### Integration Points
- Config loader (Phase 1) provides the SiteConfig object that drives all Phase 2 components
- Structured logging (Phase 1) provides the logger that Phase 2 components bind context to
- Politeness controller (Phase 1) provides delay enforcement and robots.txt checking
- Phase 2 outputs raw extracted records that Phase 3's validation pipeline will consume

</code_context>

<deferred>
## Deferred Ideas

- Adaptive delay / auto-throttle based on server response times -- v2 feature (RES-V2-01)
- httpx optimization for static pages -- can be added per-level after Playwright path works
- Concurrent fetching with semaphore -- optimization after sequential path is validated
- Browser pool for Playwright -- only needed at 50K+ page scale, out of scope

</deferred>

---

*Phase: 02-crawl-engine*
*Context gathered: 2026-03-13*
