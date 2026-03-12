# Phase 2: Crawl Engine - Research

**Researched:** 2026-03-13
**Status:** Complete
**Phase Goal:** User can point the tool at a real multi-level directory and get raw extracted records from all levels, with JS rendering, pagination, and retry handling

## Component Architecture

The crawl engine decomposes into five components that map directly to the requirements:

### 1. Fetcher (JS-01, JS-02, JS-03)

**Dual-mode design** with a shared async Protocol:

```python
class Fetcher(Protocol):
    async def fetch(self, url: str, wait_selector: str | None = None, timeout: float = 15.0) -> str: ...
    async def close(self) -> None: ...
```

**PlaywrightFetcher** (browser-rendered pages):
- Single browser instance for entire crawl session (`playwright.chromium.launch()`)
- Single browser context (`browser.new_context()`)
- Create/close individual `Page` objects per fetch call -- avoids stale state between pages
- Page lifecycle per fetch:
  1. `page = await context.new_page()`
  2. `await page.goto(url, wait_until="domcontentloaded", timeout=30000)`
  3. If `wait_selector`: `await page.wait_for_selector(wait_selector, timeout=timeout*1000)`
  4. Else: `await page.wait_for_load_state("networkidle", timeout=timeout*1000)`
  5. `html = await page.content()`
  6. `await page.close()`
  7. Return html
- On timeout in step 3/4: log warning with URL, return whatever HTML is available (partial extraction better than skip)
- Playwright Python async API: `async_playwright()` context manager, all methods are `await`-able

**HttpxFetcher** (static pages):
- Uses `httpx.AsyncClient` with connection pooling
- Timeout configuration: `httpx.Timeout(30.0, connect=10.0, read=30.0)`
- Returns `response.text` (HTML string)
- Config chooses fetcher per level via `renderer: "browser" | "static"`

**Infinite scroll handling** (JS-02):
- Implemented as a method on PlaywrightFetcher, not a separate component
- Pattern: scroll to bottom, wait for new content, repeat until no new items or max reached
- Uses `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`
- Detection: count items matching a selector before/after scroll; stop when count unchanged after wait
- Configurable max_items cap prevents runaway scrolling

### 2. Extractor (EXT-01 through EXT-05)

**BeautifulSoup4 + lxml** for all HTML parsing after fetch:

- Fetcher returns raw HTML string; Extractor parses it with `BeautifulSoup(html, "lxml")`
- This avoids repeated Python-to-browser bridge crossings that Playwright's `query_selector_all` would cause
- Per-field extraction with fallback selector chains (EXT-05):
  ```python
  def extract_field(soup, selectors: list[str]) -> str | None:
      for selector in selectors:
          el = soup.select_one(selector)
          if el:
              return el.get_text(strip=True)
      return None  # Missing fields -> null, not skip (EXT-02)
  ```
- Fields defined in config under each level's `fields` list
- Each field has: `name`, `selectors` (priority list), `attribute` (optional -- defaults to text content, but can be "href", "src", etc.)
- Link extraction for navigation: `soup.select(link_selector)` returns all matching `<a>` tags, extract `href` attribute
- Context extraction: `soup.select_one(context_selector)` extracts the identity label for ancestor metadata (EXT-03)

### 3. URL Frontier (NAV-01, NAV-02, NAV-04)

**In-memory URL management** with per-level queues:

```python
@dataclass
class FrontierItem:
    url: str
    depth: int
    ancestors: list[dict]  # [{level_name: str, label: str, url: str}, ...]

class URLFrontier:
    def __init__(self):
        self._visited: set[str] = set()
        self._queues: dict[int, deque[FrontierItem]] = defaultdict(deque)

    def add(self, url: str, depth: int, ancestors: list[dict]) -> bool:
        normalized = self._normalize(url)
        if normalized in self._visited:
            return False
        self._visited.add(normalized)
        self._queues[depth].append(FrontierItem(normalized, depth, ancestors))
        return True

    def pop(self, depth: int) -> FrontierItem | None:
        queue = self._queues.get(depth)
        return queue.popleft() if queue else None

    def has_pending(self, depth: int) -> bool:
        return bool(self._queues.get(depth))
```

**URL normalization** (NAV-04):
- Strip trailing slashes
- Lowercase scheme and host
- Sort query parameters alphabetically
- Remove default ports (80 for http, 443 for https)
- Remove URL fragments (#)
- Use `urllib.parse.urlparse` / `urlunparse` for decomposition/recomposition

### 4. Pagination Handler (NAV-03, JS-02)

Three pagination strategies, config-selected per level:

**next_page:**
- Extract href from pagination selector (e.g., `a.next-page`)
- Resolve relative URLs against current page URL using `urllib.parse.urljoin`
- Follow until selector not found or max_pages reached
- Each page goes through the normal fetch -> extract cycle

**load_more:**
- Uses PlaywrightFetcher (requires browser interaction)
- Click the load-more button via `page.click(selector)`
- Wait for new content: `page.wait_for_selector(content_selector, state="attached")`
- Repeat until button disappears or max_pages reached
- Returns accumulated HTML after all loads complete

**infinite_scroll:**
- Scroll via `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`
- Count items before/after scroll using item selector
- Stop when: count unchanged after 3 consecutive scrolls, or max_items reached
- Wait between scrolls: 1-2 seconds for content to load

**Safety cap:** `max_pages` per level (default: 100) prevents infinite loops from misconfigured pagination.

### 5. Orchestrator (ties everything together)

**Level-based BFS traversal:**

```
for each level in config.levels (ordered by depth):
    while frontier.has_pending(level.depth):
        item = frontier.pop(level.depth)

        # Fetch
        html = await fetcher.fetch(item.url, wait_selector=level.wait_selector)

        # Handle pagination (accumulate all pages of results)
        all_html = await pagination_handler.paginate(html, level, item.url)

        # Extract
        if level.is_detail_page:
            record = extractor.extract_record(all_html, level.fields, item.ancestors)
            records.append(record)
        else:
            # Extract child links for next level
            links = extractor.extract_links(all_html, level.link_selector)
            context_label = extractor.extract_context(all_html, level.context_selector)

            ancestors = item.ancestors + [{
                "level": level.name,
                "label": context_label,
                "url": item.url
            }]

            for link in links:
                full_url = urljoin(item.url, link)
                frontier.add(full_url, level.depth + 1, ancestors)

        # Polite delay (from Phase 1's politeness controller)
        await delay_controller.wait()
```

**Key design decisions:**
- Levels processed sequentially (depth 0 fully complete before depth 1 starts)
- Within a level, URLs processed sequentially (polite crawling)
- Pagination is handled inline -- a paginated listing page produces multiple HTML documents that are all extracted before moving to the next URL
- The orchestrator does NOT handle retry logic -- that's the fetcher's responsibility via tenacity

## Retry and Resilience Patterns (RES-01, RES-02)

**tenacity wraps the fetch function**, not individual operations:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

class RateLimitError(Exception):
    """Raised on HTTP 429"""
    pass

class ServerError(Exception):
    """Raised on HTTP 5xx"""
    pass

# For 429 responses
@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=5, min=5, max=60),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def fetch_with_rate_limit_retry(fetcher, url, **kwargs):
    ...

# For 5xx responses
@retry(
    retry=retry_if_exception_type(ServerError),
    wait=wait_fixed(10),
    stop=stop_after_attempt(2),  # 1 retry = 2 attempts
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def fetch_with_server_retry(fetcher, url, **kwargs):
    ...
```

**Error classification in the fetcher:**
- HTTP 429 -> raise `RateLimitError` (triggers exponential backoff)
- HTTP 5xx -> raise `ServerError` (triggers single retry after 10s)
- HTTP 404 -> log and return None (not an error, listing removed)
- Connection timeout -> log and return None (skip page)
- Playwright timeout -> log warning, return partial HTML if available

**tenacity async support:** The `@retry` decorator works directly on `async def` functions. No special async adapter needed -- tenacity detects the coroutine and uses `asyncio.sleep` automatically.

## Hierarchical Context Propagation (EXT-03)

Each URL carries its ancestry through the `FrontierItem.ancestors` list:

1. **Level 0 (homepage):** Seed URL added with empty ancestors
2. **Level 1 (regions):** Each region link extracted with ancestors = `[{level: "homepage", label: "Directory Name", url: "..."}]`
3. **Level 2 (listings):** Each listing link carries ancestors = `[...parent_ancestors, {level: "region", label: "California", url: "..."}]`
4. **Level 3 (detail):** Record extraction includes `region` and `category` fields populated from ancestors

The `context_selector` field in config specifies what text to extract as the label for each non-detail level (e.g., `h1.region-title` for region pages).

## Config Schema (relevant fields for Phase 2)

```yaml
site:
  name: "Example Directory"
  base_url: "https://example.com/directory"

levels:
  - depth: 0
    name: "homepage"
    link_selector: "a.region-link"
    context_selector: "h1"
    renderer: "browser"  # or "static"
    wait_selector: ".region-list"
    pagination: null

  - depth: 1
    name: "region"
    link_selector: "a.listing-link"
    context_selector: "h1.region-title"
    renderer: "browser"
    wait_selector: ".listing-grid"
    pagination:
      type: "next_page"  # or "load_more" or "infinite_scroll"
      selector: "a.next-page"
      max_pages: 50

  - depth: 2
    name: "detail"
    is_detail_page: true
    renderer: "browser"
    wait_selector: ".business-details"
    fields:
      - name: "business_name"
        selectors: ["h1.biz-name", "h1.listing-title", ".business-name"]
        attribute: null  # text content
      - name: "address"
        selectors: [".street-address", ".address", "[itemprop='address']"]
      - name: "phone"
        selectors: [".phone", "a[href^='tel:']", "[itemprop='telephone']"]
      - name: "website"
        selectors: ["a.website-link", "a[rel='nofollow']"]
        attribute: "href"
      - name: "description"
        selectors: [".description", ".about", ".business-desc"]

delays:
  min: 1.0
  max: 3.0

timeouts:
  navigation: 30
  wait_selector: 15

retry:
  rate_limit_max_attempts: 3
  rate_limit_backoff_start: 5
  rate_limit_backoff_max: 60
  server_error_retry_delay: 10
```

## Validation Architecture

### Testing Strategy

**Unit tests (pytest, mocked):**
- URL normalization edge cases
- Extractor with pre-built HTML strings (no network)
- Frontier add/pop/dedup logic
- Pagination detection (selector presence/absence)
- Ancestor propagation through frontier items

**Integration tests (pytest, real Playwright):**
- PlaywrightFetcher against a local test server (pytest-httpserver or aiohttp test server)
- Serve static HTML files that simulate a 3-level directory
- Test JS rendering with a simple page that uses JavaScript to populate content
- Test infinite scroll with a page that loads items on scroll events
- Test load_more with a page that reveals content on button click

**Test fixtures:**
- Static HTML files representing each level type (homepage with links, listing with pagination, detail with fields)
- A JS-rendered page that populates content after 500ms delay
- A paginated listing with 3 pages of results

**End-to-end validation:**
- Run the orchestrator against the local test server
- Verify: all 3 levels traversed, all records extracted, no duplicate URLs fetched
- Verify: ancestor context propagated to detail records
- Verify: pagination followed to completion (all pages)

### Nyquist Validation Dimensions

1. **Correctness:** Records extracted match expected data from test fixtures
2. **Completeness:** All reachable pages visited, no records missed
3. **Resilience:** 404s and timeouts logged and skipped without crash
4. **Context integrity:** Every record carries correct region/category from ancestors
5. **Deduplication:** Same URL never fetched twice (verified via fetch call counter)
6. **JS rendering:** Content populated by JavaScript is captured (not empty)
7. **Pagination:** All pages of paginated listings processed
8. **Config-driven:** Behavior changes correctly when config selectors/settings change

## Dependencies on Phase 1

Phase 2 assumes these Phase 1 deliverables exist:
- `SiteConfig` dataclass loaded from YAML (CFG-01)
- CLI entry point with argument parsing (CFG-02)
- Config schema validation (CFG-03)
- Structured logger with context binding (RES-06)
- Politeness controller: delay enforcement + robots.txt checking (RES-03, RES-04)

If Phase 1 is not complete, Phase 2 plans should define stub interfaces for these components so development can proceed.

## Key Library Patterns

### Playwright Python (async)
```python
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_selector(selector, timeout=15000)
    html = await page.content()
    await page.close()
    # browser and context stay open for reuse
```

### tenacity async retry
```python
@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=5, min=5, max=60),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def fetch_page(url: str) -> str:
    # tenacity auto-detects async and uses asyncio.sleep
    ...
```

### httpx async client
```python
async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
    response = await client.get(url)
    if response.status_code == 429:
        raise RateLimitError()
    if response.is_server_error:
        raise ServerError()
    return response.text
```

### BeautifulSoup4 with lxml
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "lxml")
# CSS selector for single element
element = soup.select_one("h1.title")
text = element.get_text(strip=True) if element else None
# CSS selector for multiple elements
links = soup.select("a.listing-link")
hrefs = [a.get("href") for a in links if a.get("href")]
```

---

## RESEARCH COMPLETE

Phase 2 research covers: component architecture (fetcher, extractor, frontier, pagination, orchestrator), retry/resilience patterns with tenacity, hierarchical context propagation, config schema for crawl engine, validation strategy with local test server, and key library API patterns for Playwright, httpx, BS4, and tenacity.
