# Architecture Research

**Domain:** Config-driven, multi-level web directory scraper with JS rendering
**Researched:** 2026-03-13
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI / Entry Point                       │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Config Loader │  │ CLI Args     │                             │
│  └──────┬───────┘  └──────┬───────┘                             │
│         └────────┬────────┘                                     │
│                  ▼                                               │
├─────────────────────────────────────────────────────────────────┤
│                       Crawl Orchestrator                        │
│  (drives the crawl: level traversal, state, scheduling)         │
├──────────┬──────────────────┬───────────────────┬───────────────┤
│          ▼                  ▼                   ▼               │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐      │
│  │ URL Frontier  │  │  Politeness   │  │  Checkpoint /   │      │
│  │ (queue +      │  │  Controller   │  │  State Manager  │      │
│  │  dedup set)   │  │  (delays,     │  │  (resume on     │      │
│  │              │  │   robots.txt) │  │   interruption) │      │
│  └──────┬───────┘  └───────┬───────┘  └─────────────────┘      │
│         │                  │                                    │
│         ▼                  ▼                                    │
├─────────────────────────────────────────────────────────────────┤
│                        Fetcher Layer                            │
│  ┌──────────────────┐  ┌────────────────────┐                   │
│  │  httpx (static)  │  │  Playwright (JS)   │                   │
│  └──────────────────┘  └────────────────────┘                   │
│         │                       │                               │
│         └───────────┬───────────┘                               │
│                     ▼                                           │
├─────────────────────────────────────────────────────────────────┤
│                       Extractor Layer                           │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Selector-driven extraction (CSS/XPath via BS4)      │       │
│  │  Config maps: field_name → selector expression       │       │
│  └──────────────────────┬───────────────────────────────┘       │
│                         ▼                                       │
├─────────────────────────────────────────────────────────────────┤
│                     Data Pipeline                               │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌───────────┐   │
│  │  Cleaner   │  │ Validator  │  │  Dedup   │  │ Reporter  │   │
│  │ (normalize,│  │ (phone,    │  │ (by key  │  │ (stats,   │   │
│  │  strip,    │  │  URL,      │  │  fields) │  │  quality) │   │
│  │  decode)   │  │  schema)   │  │          │  │           │   │
│  └─────┬──────┘  └─────┬──────┘  └────┬─────┘  └─────┬─────┘   │
│        └───────────┬────┘              │              │         │
│                    ▼                   ▼              ▼         │
├─────────────────────────────────────────────────────────────────┤
│                       Output Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  CSV Writer  │  │  JSON Writer │  │  Validation      │       │
│  │              │  │  (nested)    │  │  Report Writer   │       │
│  └──────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Config Loader | Parse YAML/JSON site config, merge CLI overrides, validate schema | PyYAML + dataclass or Pydantic model for validation |
| CLI Entry Point | Accept command-line arguments, select config, kick off crawl | argparse or click; thin layer that delegates to orchestrator |
| Crawl Orchestrator | Drive the multi-level traversal: process each level's URLs, feed extracted links to the next level, coordinate all components | Async main loop with level-aware processing; the "brain" |
| URL Frontier | Store pending URLs per level, track visited URLs, prevent duplicates | In-memory set for visited URLs + deque per crawl level |
| Politeness Controller | Enforce delays, respect robots.txt, back off on 429/5xx | urllib.robotparser or protego for robots.txt; asyncio.sleep with jitter |
| Checkpoint / State Manager | Persist crawl progress to disk; enable resume on interruption | JSON file with visited URLs, pending queue, extracted records |
| Fetcher (httpx) | Fetch static HTML pages efficiently with connection pooling | httpx.AsyncClient with retries and timeout config |
| Fetcher (Playwright) | Render JS-heavy pages, handle dynamic content loading | playwright.async_api with shared browser context |
| Extractor | Apply CSS/XPath selectors from config to parse fields from HTML | BeautifulSoup4; selector map from config drives extraction |
| Cleaner | Normalize whitespace, decode HTML entities, strip tags | String operations, html.unescape, regex for phone normalization |
| Validator | Validate extracted field values (URL format, phone format, required fields) | Regex patterns + custom validation functions |
| Record Deduplicator | Remove duplicate records by composite key (name+address or URL) | Set of hashed composite keys |
| Reporter | Track and report crawl statistics: records, completeness, errors, duration | Counters accumulated during crawl, summary dict at end |
| CSV Writer | Write flat records with correct encoding and headers | pandas DataFrame or csv.DictWriter with utf-8-sig encoding |
| JSON Writer | Write records preserving hierarchical region/category nesting | json.dump with nested dict structure grouped by level ancestry |

## Recommended Project Structure

```
multi-level-directory-scraper/
├── src/
│   └── scraper/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point, argument parsing
│       ├── config.py           # Config loading, validation, merging
│       ├── orchestrator.py     # Crawl orchestrator (level traversal loop)
│       ├── frontier.py         # URL queue + deduplication set
│       ├── politeness.py       # Rate limiting, robots.txt, backoff
│       ├── state.py            # Checkpoint persistence, resume logic
│       ├── fetcher.py          # Fetcher interface + httpx/Playwright impls
│       ├── extractor.py        # Selector-driven field extraction
│       ├── pipeline.py         # Cleaning, validation, dedup pipeline
│       ├── output.py           # CSV/JSON/report writers
│       └── logging.py          # Structured logging setup
├── configs/
│   └── example_site.yaml       # Example site configuration
├── tests/
│   ├── test_config.py
│   ├── test_frontier.py
│   ├── test_extractor.py
│   ├── test_pipeline.py
│   ├── test_output.py
│   └── test_orchestrator.py
├── output/                     # Default output directory (gitignored)
├── pyproject.toml
└── README.md
```

### Structure Rationale

- **src/scraper/:** Single flat package. The project is mid-complexity (not a framework, not a script). Flat structure avoids premature nesting while keeping each concern in its own module. Every module maps to one component from the architecture diagram.
- **configs/:** Separate directory for site configs keeps them distinct from code. Users add new sites by adding YAML files here, not by touching Python.
- **tests/:** Mirror the source structure. Each module gets its own test file. Integration tests for orchestrator test the full flow with mocked fetcher.
- **output/:** Gitignored. Default landing zone for CSV/JSON/reports so runs don't clutter the project root.

## Architectural Patterns

### Pattern 1: Level-Based Crawl Orchestration

**What:** The orchestrator processes URLs in discrete levels (Level 0: seed URLs, Level 1: region pages, Level 2: listing pages, Level 3: detail pages). Each level completes before the next begins. At each level, the extractor produces either "links to follow" (fed into the next level's frontier) or "data records" (fed into the pipeline).

**When to use:** Hierarchical directory scraping where each level has a distinct page type with different selectors and different output (links vs. data).

**Trade-offs:** Simpler to reason about and checkpoint than depth-first traversal. Slightly higher memory (stores all URLs for a level before processing), but directory sites at any single level are bounded (hundreds to low thousands of URLs, not millions). BFS order also avoids crawler traps where DFS could get stuck in a deep branch.

**Example:**
```python
async def run_crawl(config: SiteConfig):
    frontier = URLFrontier()
    frontier.add_urls(config.seed_urls, level=0)

    for level in config.levels:
        urls = frontier.get_urls(level.depth)
        async for url in urls:
            html = await fetcher.fetch(url)
            if level.is_detail_page:
                record = extractor.extract_record(html, level.selectors)
                pipeline.process(record, context={"ancestors": url.ancestors})
            else:
                links = extractor.extract_links(html, level.link_selector)
                frontier.add_urls(links, level=level.depth + 1,
                                  ancestors=url.ancestors + [url])
```

### Pattern 2: Config-Driven Selector Mapping

**What:** Site-specific selectors, URL patterns, pagination rules, and field definitions live entirely in YAML config. The Python code is generic -- it reads config and applies it. Adding a new target site means writing a new YAML file, not new Python code.

**When to use:** Always, for this project. It is the core design principle (per PROJECT.md).

**Trade-offs:** Slightly more upfront work to build the config schema and loader. Massive payoff: demonstrates software design maturity in portfolio, enables testing extraction logic against different configs, and separates concerns cleanly.

**Example config structure:**
```yaml
site:
  name: "example_directory"
  base_url: "https://example.com"
  robots_txt: true
  request_delay:
    min: 1.0
    max: 3.0
  js_rendering: true

levels:
  - depth: 0
    name: "regions"
    start_urls:
      - "https://example.com/regions"
    link_selector: "a.region-link"
    url_pattern: "/regions/[^/]+"

  - depth: 1
    name: "listings"
    link_selector: "div.listing a.title"
    url_pattern: "/business/\\d+"
    pagination:
      type: "next_page"              # next_page | load_more | infinite_scroll
      selector: "a.next-page"

  - depth: 2
    name: "detail"
    is_detail_page: true
    fields:
      name: "h1.business-name::text"
      address: "span.address::text"
      phone: "a.phone::text"
      website: "a.website::attr(href)"
      description: "div.description::text"
      category: "span.category::text"
```

### Pattern 3: Dual-Mode Fetcher with Shared Interface

**What:** A fetcher abstraction that dispatches to either httpx (fast, lightweight, for static pages) or Playwright (heavy, for JS-rendered pages). The config determines which is used -- either globally per site or per level. Both return raw HTML, hiding transport details from the extractor.

**When to use:** When some levels might be static (e.g., region index) while detail pages require JS rendering. Even if the whole site needs JS, the abstraction keeps the door open for optimization later.

**Trade-offs:** Playwright is slow and memory-heavy. Using httpx where possible dramatically speeds up crawls. The abstraction adds minimal complexity (a protocol class with one method) but enables this optimization. For the initial build, defaulting everything to Playwright is fine -- optimize to httpx for specific levels later.

**Example:**
```python
from typing import Protocol

class Fetcher(Protocol):
    async def fetch(self, url: str) -> str: ...

class HttpxFetcher:
    async def fetch(self, url: str) -> str:
        response = await self.client.get(url)
        return response.text

class PlaywrightFetcher:
    async def fetch(self, url: str) -> str:
        page = await self.context.new_page()
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        await page.close()
        return content
```

### Pattern 4: Pipeline-Stage Processing

**What:** Extracted records pass through a sequence of processing stages: clean -> validate -> deduplicate -> accumulate. Each stage is a function or class with a single responsibility. The pipeline is composable -- stages can be added, removed, or reordered.

**When to use:** Always for data quality. This is the Scrapy Item Pipeline pattern adapted for a non-Scrapy project.

**Trade-offs:** Slightly more code than dumping everything into one function. But each stage is independently testable, and the pipeline composition makes data quality rules explicit and auditable.

## Data Flow

### Crawl Execution Flow

```
[CLI invokes orchestrator with merged config]
    │
    ▼
[Orchestrator loads checkpoint (if resuming)]
    │
    ▼
[For each level in config.levels:]
    │
    ├──▶ [Frontier yields next URL for this level]
    │        │
    │        ▼
    │    [Politeness Controller: check robots.txt, apply delay]
    │        │
    │        ▼
    │    [Fetcher: httpx or Playwright based on config]
    │        │
    │        ▼
    │    [Extractor: apply level's selectors to HTML]
    │        │
    │        ├── [Links found?] ──▶ [Add to frontier at next level depth]
    │        │
    │        └── [Detail page?] ──▶ [Pipeline: clean → validate → dedup]
    │                                    │
    │                                    ▼
    │                               [Accumulate record with ancestors]
    │        │
    │        ▼
    │    [Checkpoint: persist state periodically]
    │        │
    │        └──▶ [Back to frontier for next URL]
    │
    ▼
[All levels complete]
    │
    ▼
[Output: write CSV, write JSON, write validation report]
```

### Checkpoint / State Flow

```
[During crawl:]
    Periodically (every N URLs or on signal):
        Save to crawl_state.json:
        {
            "current_level": 1,
            "visited_urls": [...],
            "pending_urls_by_level": {0: [], 1: [...], 2: [...]},
            "extracted_records": [...],
            "stats": {"fetched": 142, "errors": 3, ...}
        }

[On SIGINT / SIGTERM:]
    1. Finish current fetch (or abort gracefully)
    2. Save final state
    3. Write partial results to output files
    4. Exit cleanly

[On resume:]
    1. Load crawl_state.json
    2. Rebuild frontier from pending URLs
    3. Rebuild visited set from visited URLs
    4. Continue from where interrupted
```

### Key Data Flows

1. **URL Discovery:** Seed URLs -> Frontier (level 0) -> Fetcher -> Extractor finds links -> Frontier (level 1) -> ... repeats until detail level.
2. **Data Extraction:** Detail page HTML -> Extractor (selectors from config) -> Raw record dict -> Pipeline stages -> Clean, validated record.
3. **Hierarchical Context Propagation:** Each URL carries its "ancestors" (which region page, which listing page led to it). This context attaches to extracted records so the output preserves the directory hierarchy (region/category per record).
4. **Error Recovery:** Fetch failure -> Retry with exponential backoff (up to 3 retries) -> On permanent failure, log error and skip URL -> URL marked as visited (with error) to prevent re-fetching on resume.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Small site (<1K pages) | Single-threaded async is sufficient. All state in memory. Checkpoint to single JSON file. This is the target scale. |
| Medium site (1K-50K pages) | Add concurrency with asyncio.Semaphore (3-5 concurrent fetches). Batch checkpoint writes. Consider SQLite for state instead of JSON. |
| Large site (50K+ pages) | Out of scope per PROJECT.md. Would need: connection pooling, browser pool for Playwright, disk-backed frontier, incremental output writes. |

### Scaling Priorities

1. **First bottleneck: Fetch latency.** Each page takes 1-5 seconds (network + politeness delay). With 1K pages at 2s average, that is 33 minutes. Acceptable for a batch tool. If needed, semaphore-bounded concurrency is the first lever.
2. **Second bottleneck: Playwright memory.** Each browser context uses ~50-100MB. Reuse a single context, create/close pages per request. Never open multiple browsers.

## Anti-Patterns

### Anti-Pattern 1: Hardcoded Selectors in Python Code

**What people do:** Put CSS selectors directly in the extraction functions, or worse, scattered across multiple files.
**Why it's wrong:** Adding a new site or handling selector changes requires code changes, testing, and redeployment. Mixes data concerns (what to extract) with logic concerns (how to extract).
**Do this instead:** All selectors live in YAML config. Python code reads selectors from config and applies them generically. The extractor function never contains a literal selector string.

### Anti-Pattern 2: Recursive Crawling Without Depth Bounds

**What people do:** Follow every link found on every page, recursively, without tracking depth or restricting to expected URL patterns.
**Why it's wrong:** Crawler traps (infinite calendars, session URLs, query parameter variations) cause infinite loops. Memory grows unbounded. The scraper never finishes.
**Do this instead:** Explicit level definitions with URL pattern filters. Only follow links matching the expected pattern for the next level. Cap max depth to the number of configured levels.

### Anti-Pattern 3: Launching a New Browser Per Page

**What people do:** Call `browser.launch()` or create a new `BrowserContext` for every page fetch.
**Why it's wrong:** Browser launch takes 500ms-2s and ~100MB RAM. For hundreds of pages, this is catastrophically slow and will OOM.
**Do this instead:** Launch one browser at crawl start, create one persistent context, create/close individual `Page` objects per fetch. The browser lives for the entire crawl session.

### Anti-Pattern 4: No Partial Output on Failure

**What people do:** Accumulate all records in memory and write output only at the very end.
**Why it's wrong:** A crash at 90% completion loses everything. Especially painful for long-running scrapes.
**Do this instead:** Implement checkpoint persistence. Write partial results on interruption signal. On resume, load previous state and continue. Even without resume, partial output is better than no output.

### Anti-Pattern 5: Ignoring Hierarchical Context

**What people do:** Extract detail page fields but lose track of which region/category the record came from.
**Why it's wrong:** The directory hierarchy IS the data structure. A business listing without its region/category context is significantly less useful.
**Do this instead:** Propagate ancestor context through the crawl. Each URL in the frontier carries metadata about which parent pages led to it. Attach this to extracted records.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Target website | HTTP/HTTPS via httpx or Playwright | Respect robots.txt, rate limit, handle errors |
| robots.txt | urllib.robotparser or protego library | Fetch once at crawl start, cache for session |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Config -> All components | Config dataclass passed at init | Immutable after loading; components read but never mutate config |
| Orchestrator -> Fetcher | Async method call: `fetch(url) -> html` | Fetcher is stateless per call; orchestrator manages sequencing |
| Orchestrator -> Frontier | `add_urls()`, `get_urls(level)`, `mark_visited()` | Frontier owns URL state; orchestrator drives iteration |
| Extractor -> Pipeline | Returns raw dict; pipeline processes it | Clean boundary: extractor never validates, pipeline never parses HTML |
| Pipeline -> Output | Pipeline yields clean records; output writes them | Output is invoked once at end (or on checkpoint for partial writes) |
| State Manager <-> Orchestrator | `save_state()` / `load_state()` | State manager serializes; orchestrator decides when to checkpoint |

## Build Order (Dependency Chain)

Components should be built in this order based on dependencies:

```
Phase 1: Foundation (no dependencies)
    ├── Config loader + schema
    ├── Structured logging
    └── CLI skeleton

Phase 2: Fetch + Extract (depends on config)
    ├── Fetcher (Playwright first, httpx later)
    ├── Extractor (selector-driven, depends on config schema)
    └── Politeness controller (robots.txt, delays)

Phase 3: Crawl Loop (depends on fetch + extract)
    ├── URL Frontier (queue + dedup)
    ├── Orchestrator (level-based traversal)
    └── Basic end-to-end: config → fetch → extract → stdout

Phase 4: Data Quality (depends on extraction working)
    ├── Pipeline stages (clean, validate, dedup)
    ├── Record deduplication
    └── Hierarchical context propagation

Phase 5: Output + Resilience (depends on pipeline)
    ├── CSV writer
    ├── JSON writer (nested structure)
    ├── Validation report
    ├── Checkpoint / state persistence
    └── Resume from interruption

Phase 6: Polish (depends on everything)
    ├── Pagination handling (next page, load more, infinite scroll)
    ├── httpx fetcher for static pages (optimization)
    ├── Error handling hardening
    └── Portfolio README
```

## Sources

- [Scrapy Architecture Overview](https://docs.scrapy.org/en/latest/topics/architecture.html) -- gold standard reference for scraper component design (Engine, Scheduler, Downloader, Spider, Pipeline, Middleware)
- [Config-driven Scrapy spider for multiple websites](https://www.cyberangles.org/blog/using-one-scrapy-spider-for-several-websites/) -- YAML config pattern for site-specific selectors
- [Scrapy jobs: pausing and resuming crawls](https://docs.scrapy.org/en/latest/topics/jobs.html) -- checkpoint/resume pattern with JOBDIR
- [Crawl4AI Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/) -- BFS/DFS crawl strategies with depth configuration
- [Protego: Python robots.txt parser](https://github.com/scrapy/protego) -- modern robots.txt parsing
- [urllib.robotparser](https://docs.python.org/3/library/urllib.robotparser.html) -- stdlib robots.txt support
- [Web Crawler System Design](https://www.hellointerview.com/learn/system-design/problem-breakdowns/web-crawler) -- URL frontier, dedup, politeness patterns
- [Modular web scraper with Scrapy-like architecture](https://medium.com/@zakimaliki/building-a-modular-web-scraper-with-scrapy-like-architecture-16eb7f2a643c) -- component decomposition for custom scrapers

---
*Architecture research for: multi-level directory scraper*
*Researched: 2026-03-13*
