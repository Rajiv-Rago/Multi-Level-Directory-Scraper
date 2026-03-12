# Pitfalls Research

**Domain:** Multi-level directory scraping with JS rendering (Python/Playwright)
**Researched:** 2026-03-13
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Silent Selector Breakage

**What goes wrong:**
The scraper runs successfully, returns data, and exits with no errors -- but the data is wrong or empty. A website updates its layout, renames CSS classes, or restructures its HTML, and the selectors configured in YAML silently stop matching. The scraper dutifully returns empty strings or `None` for every field instead of crashing with a clear error. You end up with thousands of rows of blank data and no indication anything went wrong.

**Why it happens:**
CSS selectors and XPath expressions are tightly coupled to a site's DOM structure. Sites change layouts routinely -- new designs, A/B tests, framework upgrades. Selectors like `div.listing-card > h2 > a` or auto-generated XPath like `/div[3]/span[2]` are extremely brittle. When nothing matches, BeautifulSoup returns `None`, which silently propagates through data pipelines.

**How to avoid:**
- Validate extraction results immediately after scraping each page. If all fields are null/empty on a page that loaded successfully, that is a selector failure -- raise an error, not a warning.
- Implement a "canary check": before a full run, scrape 1-2 known pages and verify expected fields are populated. Abort if the canary fails.
- Use semantic CSS selectors (`.product-title`, `.business-name`) rather than positional ones (`div:nth-child(3) > span`). Semantic selectors survive minor layout changes.
- Log the number of fields extracted per page. A sudden drop to zero across pages is a signal.

**Warning signs:**
- Output CSV has empty columns that previously had data
- Record count is correct but field completeness drops to 0%
- No errors in logs despite obviously bad output

**Phase to address:**
Core extraction engine phase. Build field validation directly into the extraction pipeline from the start. Never treat extraction as "parse and hope."

---

### Pitfall 2: Playwright Memory Accumulation in Long Crawls

**What goes wrong:**
The scraper starts fine but gradually consumes more and more RAM until it crashes, the OS kills it, or the machine becomes unresponsive. For a multi-level directory with thousands of pages, this can happen within the first run.

**Why it happens:**
Playwright's `BrowserContext` accumulates `ChannelOwner` instances (Request, Response objects) internally in `Connection._objects`. These are only flushed when the context is closed. If you reuse the same browser context for thousands of page navigations, memory grows unboundedly. Additionally, `page.on()` event listeners and `page.route()` handlers accumulate objects that are not cleaned up. Each browser context uses 50-100MB RAM baseline, and each page navigation adds to that without cleanup.

**How to avoid:**
- Rotate browser contexts periodically -- close and recreate the context every N pages (50-100 is a reasonable interval). This flushes accumulated Request/Response objects.
- Close pages after extracting data. Do not keep page references alive.
- Use `try/finally` blocks to ensure `page.close()` and `context.close()` happen even on exceptions.
- Avoid attaching `page.on()` listeners in loops without cleanup.
- Monitor RSS memory during development. If memory grows linearly with pages scraped, you have a leak.
- Set a hard memory ceiling: if RSS exceeds a threshold, checkpoint and restart.

**Warning signs:**
- Scraper slows down over time (OS starts swapping)
- OOM kills in system logs
- Scraper completes small test runs but crashes on full directory runs
- Memory usage visible via `htop` or `ps` grows linearly with pages processed

**Phase to address:**
Browser automation phase (Playwright integration). Context rotation must be a first-class design concern, not bolted on after the memory problems appear. Build the page processing loop with context lifecycle management from the start.

---

### Pitfall 3: Losing Hierarchical Context Across Navigation Levels

**What goes wrong:**
The scraper successfully extracts detail-page data (business name, phone, address) but loses which region or category that business belonged to. The final output has flat records with no way to reconstruct which region page led to which listing. Or worse, records get associated with the wrong parent due to async processing or incorrect state management.

**Why it happens:**
In a multi-level scraper (regions -> listings -> details), the parent context (which region, which category) exists at navigation time but must be explicitly threaded through to the detail page extraction. Developers often extract detail pages in isolation, forgetting to pass the region/category metadata along. With concurrent processing, the shared state that tracks "current region" can race and assign wrong parents.

**How to avoid:**
- Design the crawl data structure to carry parent context explicitly. Each URL to be scraped should be a tuple/dataclass of `(url, parent_context)` where `parent_context` contains region name, category, and any other hierarchical metadata.
- Never rely on mutable shared state to track "where we are in the hierarchy." Each work item must be self-contained.
- Test with a small directory that has known structure: manually verify that every detail record maps back to the correct region/category.

**Warning signs:**
- All records have the same region/category (the last one processed)
- Region counts don't match expected distribution
- Records appear under wrong parents when spot-checked

**Phase to address:**
Navigation/crawl engine phase. The data model for crawl tasks must include parent context from the beginning. This is an architectural decision, not something fixable later without rewriting the crawl queue.

---

### Pitfall 4: Unreliable Page-Ready Detection

**What goes wrong:**
The scraper navigates to a page, tries to extract content, and gets either empty results or stale/partial content because the JavaScript hasn't finished rendering. This is intermittent -- works on fast connections, fails on slow ones; works for some pages, fails for others.

**Why it happens:**
JS-rendered directory sites load content asynchronously. Developers typically use one of three wait strategies, each with flaws:
- `networkidle`: Waits for no network activity for 500ms. Breaks on pages with analytics beacons, websockets, or polling (common on directory sites). Can cause 30-second timeouts.
- `load` event: Only waits for initial HTML load. JS-rendered content is not ready yet.
- Hardcoded `sleep()`: Unreliable, wastes time on fast pages, insufficient for slow ones.

**How to avoid:**
- Use `wait_for_selector()` targeting the specific content container you need to extract. This is the most reliable approach: wait for the element you actually need, not for generic page readiness.
- Implement a two-stage wait: `goto()` with `wait_until='domcontentloaded'`, then `wait_for_selector('.listing-container', timeout=15000)`.
- For infinite scroll / load-more: wait for the specific new content elements, not network idle.
- Make the wait selector configurable per-level in the YAML config, since different directory levels may have different content containers.
- Add a retry with a fresh page load if the target selector is not found after timeout.

**Warning signs:**
- Intermittent empty extractions that succeed on retry
- Scraper works locally but fails in CI/cloud (different network speeds)
- Timeout errors on specific pages but not others
- Using `time.sleep()` anywhere in the scraping pipeline

**Phase to address:**
Browser automation phase. Wait strategies must be configurable and selector-based from the start. Avoid `networkidle` as the default.

---

### Pitfall 5: No Checkpoint/Resume on Interruption

**What goes wrong:**
A scrape of 10,000+ pages runs for hours, crashes at page 8,000 (network error, memory, rate limit), and all progress is lost. The entire run must restart from scratch, re-scraping 8,000 pages unnecessarily -- wasting time and risking IP blocks from the additional requests.

**Why it happens:**
Developers build the scraper as a single pipeline: crawl all URLs, then write output. Results accumulate in memory and are only persisted at the end. No intermediate state is saved. When the process dies, everything in memory is gone.

**How to avoid:**
- Write results incrementally: append to CSV or JSONL after each page or small batch (every 10-50 pages).
- Maintain a persistent "visited URLs" set (a simple JSON file or SQLite DB). On startup, load this set and skip already-visited URLs.
- Separate the crawl frontier (URLs to visit) from results. Persist both independently.
- Use atomic writes (write to temp file, then rename) to avoid corrupted partial output.
- On graceful shutdown (SIGINT/Ctrl+C), flush current batch and save state before exiting.

**Warning signs:**
- All output is generated at the end of the run in a single write
- No files on disk until the scraper completes
- Restarting after a crash re-scrapes already-visited pages
- Ctrl+C produces no output

**Phase to address:**
Resilience/persistence phase. However, the data pipeline architecture must accommodate incremental writes from the start -- retrofitting incremental persistence onto a batch pipeline is painful.

---

### Pitfall 6: URL Deduplication Failures

**What goes wrong:**
The scraper visits the same business page multiple times because the URL appears differently in different contexts. Trailing slashes, query parameters, URL fragments, HTTP vs HTTPS, `www` vs non-`www`, tracking parameters (`?utm_source=...`), and session IDs all create "different" URLs that resolve to the same page. This wastes time, inflates record counts, and creates duplicate data.

**Why it happens:**
Naive deduplication uses raw URL string comparison. Directory sites often link to the same page with varying query parameters, capitalization, or tracking codes. Pagination can also generate duplicate links to the same listing if it appears on multiple pages of results.

**How to avoid:**
- Normalize URLs before deduplication: lowercase the domain, strip trailing slashes, remove known tracking parameters (utm_*, fbclid, etc.), remove fragments (#), sort remaining query parameters alphabetically.
- Use a URL normalization function applied consistently to every URL before it enters the visited set or crawl queue.
- For record-level dedup (in addition to URL-level): deduplicate by a composite key like (business_name + address) or (business_name + phone) since the same listing may genuinely appear under multiple category pages with different URLs.

**Warning signs:**
- Record count is significantly higher than expected for the directory size
- Duplicate rows visible in output with slightly different source URLs
- Scrape takes longer than expected (visiting same pages multiple times)

**Phase to address:**
Navigation/crawl engine phase. URL normalization must be implemented as a utility function used everywhere URLs are processed.

---

### Pitfall 7: CSV Output That Breaks in Excel/Google Sheets

**What goes wrong:**
The CSV file opens in a text editor fine but shows garbled characters, broken columns, or misaligned data when opened in Excel or Google Sheets. Phone numbers starting with `+` get interpreted as formulas. Fields containing commas, quotes, or newlines break column alignment.

**Why it happens:**
Multiple encoding and formatting issues compound:
- Excel expects UTF-8 with BOM (`utf-8-sig`) to detect encoding correctly. Plain UTF-8 CSVs show garbled non-ASCII characters (accented names, special characters in addresses).
- Fields containing the delimiter (comma) must be quoted. Fields containing quotes must have quotes escaped (doubled).
- Leading `=`, `+`, `-`, `@` in cell values trigger Excel formula interpretation (CSV injection).
- Embedded newlines in address fields break row boundaries.
- pandas `to_csv()` defaults to UTF-8 without BOM.

**How to avoid:**
- Always write CSVs with `encoding='utf-8-sig'` in pandas. This adds the BOM that Excel needs.
- Sanitize cell values: strip or escape leading `=+@-` characters to prevent formula injection.
- Strip embedded newlines from fields, or replace with spaces.
- Use pandas' built-in CSV quoting (it handles comma-in-field and quote escaping correctly by default, but verify).
- Test output by actually opening it in Excel and Google Sheets during development, not just programmatically.

**Warning signs:**
- Non-ASCII characters display as `Ã©` or similar mojibake in Excel
- Phone numbers like `+1-555-1234` show as formula errors
- Rows are misaligned (field count per row varies)
- Address fields with commas split across multiple columns

**Phase to address:**
Output/export phase. Use `utf-8-sig` encoding from the first CSV write. Add CSV injection sanitization as a post-processing step.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded selectors in code instead of config | Faster initial development | Every site change requires code changes, not config updates; defeats the config-driven architecture | Never -- config-driven is a core requirement |
| Single browser context for entire run | Simpler code, no context rotation logic | Memory leaks crash long runs; must retrofit context lifecycle later | Only for directories under ~50 pages total |
| In-memory result accumulation (no incremental writes) | Simpler data pipeline | Total data loss on crash; forces full re-scrape | Only for runs under ~5 minutes |
| `time.sleep()` instead of selector-based waits | Quick to implement, "works on my machine" | Flaky on different networks/machines; wastes time on fast pages | Never -- `wait_for_selector` is equally simple to implement |
| Raw URL string comparison for dedup | No normalization code needed | Duplicate records, wasted crawl time | Acceptable only in earliest prototype; replace immediately |
| Skip robots.txt parsing | Faster to market | Ethical violation; risk of IP ban; bad portfolio optics | Never |

## Integration Gotchas

Common mistakes when connecting to external services and tools.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Playwright browser install | Forgetting `playwright install` after pip install; CI/Docker environments missing browser binaries | Add `playwright install chromium` to setup scripts; use `--with-deps` on Linux for system libraries |
| robots.txt parsing | Checking once at startup, then ignoring `Crawl-delay` directives | Parse robots.txt per domain, honor both `Disallow` and `Crawl-delay`; re-check if scraping spans days |
| pandas CSV export | Using default `utf-8` encoding; not testing in actual Excel | Always use `encoding='utf-8-sig'`; test output in Excel/Sheets during development |
| httpx + Playwright coexistence | Using httpx for some requests and Playwright for others without sharing cookie/session state | Decide on one HTTP layer per crawl level; if Playwright is needed for JS rendering, use it consistently for that level |
| YAML config loading | No schema validation on config; typos in selector names silently produce None | Validate config on load with a schema (pydantic or jsonschema); fail fast on unknown keys or missing required fields |

## Performance Traps

Patterns that work at small scale but fail as the crawl grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Storing all results in a list/DataFrame before writing | Works for 100 records, OOM at 50K | Write incrementally to CSV/JSONL every N records; use append mode | ~10K-50K records depending on field count |
| One Playwright page per URL without closing | Tabs accumulate, each consuming 50-100MB | Close pages after extraction; pool to max 3-5 concurrent pages | ~50-100 open pages |
| Unbounded crawl queue in memory | Fine for small directories | Use a file-backed queue or deque with max size; checkpoint periodically | ~100K+ queued URLs |
| No request delay / too-short delays | Fast scraping, works initially | Implement configurable randomized delays (1-3s default); exponential backoff on 429 | First 429/block from target site |
| Full DOM parsing with BeautifulSoup on every page | Works fine for small pages | Parse only the relevant section (`soup.select_one('.main-content')`) instead of full document | Pages with heavy DOM (>5000 nodes) |
| Synchronous page processing | Simple code, easy to debug | Use async Playwright with concurrency limiter (asyncio.Semaphore); process 3-5 pages concurrently | Crawls with >1000 pages (time becomes prohibitive) |

## Security Mistakes

Domain-specific security issues for a web scraping project.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Writing scraped data containing user-submitted content to CSV without sanitization | CSV injection: cells starting with `=`, `+`, `-`, `@` execute formulas when opened in Excel | Prefix dangerous cells with a single quote or tab character; strip/escape on export |
| Storing target site credentials or API keys in config YAML | Credentials leak if config is committed to version control | Out of scope per project spec (no auth), but if added later: use environment variables, never YAML |
| Not sanitizing scraped URLs before following them | Malicious URLs (javascript:, data:) could be followed; redirect chains to unexpected domains | Validate URLs against an allowlist of domains/schemes before adding to crawl queue |
| Logging full page content at debug level | Scraper logs balloon to GB; may contain PII from directory listings | Log only URLs, status codes, and extraction summaries; never log raw HTML in production runs |

## UX Pitfalls

Common user experience mistakes for a CLI scraping tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indication during long crawls | User thinks scraper is hung; kills it, losing progress | Print progress: `[1423/8500] Scraping detail page... (Region: North)` with ETA |
| Error messages show Python tracebacks instead of actionable info | User cannot diagnose whether it is a config error, network issue, or site change | Catch known errors and print human-readable messages: "Selector '.biz-name' matched 0 elements on https://... -- check your config selectors" |
| Config validation only at runtime (mid-scrape) | Scraper runs for 30 minutes before hitting a bad selector on level 3 | Validate all config selectors against a sample page at startup; fail fast before the crawl begins |
| Output file path not configurable | User must move files after every run | Accept `--output` flag; default to `./output/{timestamp}/` |
| No dry-run mode | User must do a full scrape to test config changes | Support `--dry-run` that scrapes 2-3 pages per level and previews extracted data |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Pagination handling:** Often tested with "next page" buttons only -- verify it also handles "load more" buttons, infinite scroll, and numbered pagination. Test on the last page (no next button).
- [ ] **Data validation:** Phone normalization works for US numbers but breaks on international formats. Verify with the actual formats present in the target directory.
- [ ] **Error recovery:** Retry logic handles HTTP 429 and 5xx, but does it handle DNS resolution failures, connection resets, and SSL errors? These are common in long crawls.
- [ ] **CSV correctness:** Opens fine in your text editor, but have you opened it in Excel on Windows? Test with non-ASCII characters, commas in fields, and multi-line addresses.
- [ ] **robots.txt compliance:** Parsing `Disallow` rules is implemented, but are you also honoring `Crawl-delay`? Many directory sites set this.
- [ ] **Deduplication:** URL-level dedup works, but does record-level dedup catch the same business listed under multiple categories?
- [ ] **Hierarchical output:** JSON output has nested region/category structure, but does the CSV output still preserve region/category as columns on each row?
- [ ] **Interruption recovery:** Ctrl+C saves state, but does restart actually resume? Test: interrupt at page 50, restart, verify it starts at page 51 and final output includes all records.
- [ ] **Empty directory handling:** What happens when a region has zero listings? Does it crash, skip silently, or log appropriately?
- [ ] **Config validation:** Config loads and parses, but does it reject configs with missing required fields or typos in selector names before the crawl starts?

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent selector breakage | LOW | Fix selectors in config, re-run. If incremental writes are in place, only re-scrape affected pages. If not, full re-scrape. |
| Memory crash mid-crawl | MEDIUM | If checkpoint/resume exists: restart and resume. If not: fix memory issue, full re-scrape. This is why checkpointing is critical. |
| Lost hierarchical context | HIGH | Data cannot be retroactively assigned to correct parents without re-scraping. Must fix the crawl data model and re-run entirely. |
| Unreliable page-ready detection | LOW | Adjust wait selectors in config and re-run failed pages. If using checkpoint, only re-scrape pages that returned empty data. |
| No checkpoint, crash at 80% | HIGH | No recovery possible. Must re-scrape everything. Implement checkpointing, then re-run. |
| Duplicate records in output | LOW | Post-process: deduplicate output by composite key. Fix URL normalization to prevent on next run. |
| Broken CSV in Excel | LOW | Re-export with `utf-8-sig` encoding and sanitized cells. No re-scrape needed if raw data is intact. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent selector breakage | Core extraction engine | Canary check passes; field completeness > 90% on sample pages |
| Playwright memory accumulation | Browser automation / Playwright integration | RSS memory stays flat (not growing) across 500+ page crawl |
| Lost hierarchical context | Navigation/crawl architecture | Spot-check 20 detail records trace back to correct region/category |
| Unreliable page-ready detection | Browser automation / Playwright integration | Zero empty extractions on pages that load successfully (verified via status code) |
| No checkpoint/resume | Resilience / persistence | Interrupt at 50%, restart, final output has all records and no duplicates |
| URL deduplication failures | Navigation/crawl engine | Record count matches expected unique listings (within 5%) |
| CSV/Excel encoding issues | Output/export | Output opens correctly in Excel on Windows with non-ASCII characters intact |
| Config validation gaps | Config system / CLI | Invalid config produces clear error at startup, not mid-crawl crash |
| No progress indication | CLI / UX | User can see current progress, ETA, and error counts during a run |
| Formula injection in CSV | Output/export | Cells starting with `=+@-` are escaped; no formula execution in Excel |

## Sources

- [Memory leak while reusing BrowserContext - playwright-python #286](https://github.com/microsoft/playwright-python/issues/286)
- [Memory leak with browsers and contexts - playwright-python #2511](https://github.com/microsoft/playwright-python/issues/2511)
- [Memory increases when same context is used - playwright #6319](https://github.com/microsoft/playwright/issues/6319)
- [Memory leak in page.on and page.route - playwright-python #1754](https://github.com/microsoft/playwright-python/issues/1754)
- [How to Fix Inaccurate Web Scraping Data - Bright Data](https://brightdata.com/blog/web-data/fix-inaccurate-web-scraping-data)
- [Most Web Scrapers Break for the Same Reasons - Medium](https://yagneshmangali.medium.com/most-web-scrapers-break-for-the-same-reasons-656da4833b2f)
- [The Problem With XPath, CSS Selectors, and Keeping Your Scraper Alive](https://extractdata.substack.com/p/why-xpath-css-selectors-break-scrapers)
- [Stop Getting Blocked: 10 Common Web-Scraping Mistakes & Easy Fixes - Firecrawl](https://www.firecrawl.dev/blog/web-scraping-mistakes-and-fixes)
- [pandas to_csv utf-8-BOM issue #44323](https://github.com/pandas-dev/pandas/issues/44323)
- [Excel compatible Unicode CSV files from Python](https://tobywf.com/2017/08/unicode-csv-excel/)
- [Playwright wait strategies - Checkly Docs](https://www.checklyhq.com/docs/learn/playwright/waits-and-timeouts/)
- [networkidle clarification - playwright #22897](https://github.com/microsoft/playwright/issues/22897)
- [How to Scroll and Scrape With Playwright - ZenRows](https://www.zenrows.com/blog/playwright-scroll)
- [Rate Limiting in Web Scraping - ScrapeHero](https://www.scrapehero.com/rate-limiting-in-web-scraping/)
- [429 Status Code - What It Is and How to Avoid It - ScrapingBee](https://www.scrapingbee.com/webscraping-questions/web-scraping-blocked/429-status-code-what-it-is-and-how-to-avoid-it/)
- [URL Normalization for De-duplication - Cornell CS](https://www.cs.cornell.edu/~hema/papers/sp0955-agarwalATS.pdf)
- [Playwright Web Scraping Tutorial - Oxylabs](https://oxylabs.io/blog/playwright-web-scraping)
- [Scaling to Large Datasets - pandas documentation](https://pandas.pydata.org/docs/user_guide/scale.html)

---
*Pitfalls research for: Multi-level directory scraping with JS rendering*
*Researched: 2026-03-13*
