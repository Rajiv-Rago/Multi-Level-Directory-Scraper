# Feature Research

**Domain:** Multi-level directory scraper (config-driven, hierarchical web scraping tool)
**Researched:** 2026-03-13
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any production-quality scraper must have. Missing these means the tool looks like a toy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-level navigation (3+ depth) | Core purpose of the tool. Scrapy, Crawlee, Crawl4AI all handle recursive depth traversal. A directory scraper that can't navigate regions -> listings -> detail pages is useless. | HIGH | Requires a state machine or depth-aware URL queue. Each level needs its own selector set and link extraction logic. Most complex single feature. |
| JS-rendered content handling (Playwright) | 94% of modern websites use client-side rendering. Static HTTP requests miss most directory content. Every serious scraper in 2025+ supports headless browsers. | MEDIUM | Playwright's auto-wait handles most dynamic content. Main complexity is knowing when a page is "done loading" -- wait for network idle or specific selectors. |
| Config-driven site definitions (YAML/JSON) | Separating scraping engine from site-specific selectors is the standard pattern (Scrapy spiders, Scrapit YAML configs, Crawlee request handlers). Hardcoded selectors signal amateur work. | MEDIUM | Config schema: base URL, level definitions (selectors, pagination, field mappings), output field names. Validate config on load before crawling. |
| CSS/XPath selector-based extraction | Universal expectation. Every scraping tool from BeautifulSoup to Scrapy to browser devtools works with CSS selectors and XPath. | LOW | BeautifulSoup handles CSS selectors. lxml handles XPath. Support both; CSS is more readable, XPath more powerful for edge cases. |
| Pagination handling | Directories always paginate. Next-page links, load-more buttons, and numbered pagination are standard patterns. A scraper that only gets page 1 is broken. | MEDIUM | Three patterns to handle: (1) next-page link following, (2) click-to-load-more via Playwright, (3) URL parameter increment. Config should specify which pattern per level. |
| URL deduplication | Without it, scrapers re-visit the same pages endlessly, especially in directory sites with cross-linked categories. Scrapy, Crawlee, and Scrapling all deduplicate by default. | LOW | In-memory set of visited URLs is sufficient for single-run batch tool. Normalize URLs before comparison (strip trailing slashes, sort query params). |
| Retry with exponential backoff | Standard resilience pattern. Every production scraper handles transient failures (5xx, timeouts, connection resets). Not retrying means data loss on any hiccup. | LOW | Implement with tenacity or manual backoff. 3 retries with exponential backoff (2s, 4s, 8s) and jitter. Log each retry. |
| HTTP error handling (429, 5xx, 404) | Rate limiting (429) and server errors (5xx) are inevitable. 404s on directory listings are common as listings get removed. Must handle all three distinctly. | LOW | 429: pause and retry with longer delay. 5xx: retry with backoff. 404: log and skip (not an error for the scraper, just a missing listing). |
| robots.txt compliance | Ethical baseline. Portfolio projects especially must demonstrate responsible scraping. The robotsparser in Python's stdlib handles this. | LOW | Parse robots.txt once on startup. Check each URL against rules before requesting. Respect Crawl-delay directive if present. |
| Configurable request delays | Polite crawling is non-negotiable. 1-3s randomized delay is the standard starting point. Conservative scrapers use 10-15s. Must be configurable per-site. | LOW | Random uniform delay between min/max configured values. Applied between every request, not just per-page. |
| CSV output with proper encoding | CSV is the universal data interchange format. Must handle UTF-8 BOM for Excel compatibility, proper quoting per RFC 4180, and consistent headers. | LOW | Use Python csv module with UTF-8-sig encoding. Flatten nested data (region/category as columns). Headers from config field definitions. |
| JSON output with structure | JSON preserves hierarchical relationships that CSV flattens. Anyone doing downstream analysis wants structured data. | LOW | Nested structure: regions contain listings, listings contain detail fields. Also produce NDJSON (one record per line) for streaming/pipeline use. |
| Data validation and cleaning | Raw scraped data is always messy: whitespace, HTML entities, inconsistent formats. Validated output is what separates a tool from a script. | MEDIUM | Pipeline: strip whitespace -> decode HTML entities -> normalize phone numbers (phonenumbers library) -> validate URLs -> validate emails -> type coercion. |
| Structured logging | Without structured logs, debugging a failed crawl across thousands of pages is impossible. Every production tool (Scrapy, Crawl4AI) emits structured logs. | LOW | Python logging with JSON formatter. Include: timestamp, URL, level (region/listing/detail), status code, duration, error type if any. |
| CLI interface with argument overrides | Standard UX for CLI tools. Config file for defaults, CLI args for one-off overrides (different output dir, specific region, verbose mode). | LOW | argparse or click. Key overrides: config path, output directory, output format, delay, max pages, verbosity, dry-run flag. |

### Differentiators (Competitive Advantage)

Features that elevate this from "another scraper tutorial" to a portfolio piece demonstrating engineering judgment.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Checkpoint/resume on interruption | Most tutorial scrapers lose all progress on Ctrl+C or crash. Persisting crawl state to disk and resuming from last checkpoint demonstrates resilience engineering thinking. Crawlee and Scrapling both offer this. | HIGH | Save crawl queue state (visited URLs, pending URLs, current depth) to JSON file periodically and on SIGINT/SIGTERM. On restart, detect checkpoint file and offer to resume. |
| Validation report with data quality metrics | Raw data output is expected; a quality report that summarizes completeness, duplicates, field coverage, and error rates shows data engineering maturity. | MEDIUM | Generate after crawl: total records, records per level, field completeness percentages, duplicate count, error count by type, crawl duration, pages/second. Output as both terminal summary and JSON file. |
| Record deduplication by composite key | URL dedup prevents re-visiting pages. Record dedup catches when the same business appears under multiple categories or pagination overlaps. Uses composite key (name + address or name + phone). | MEDIUM | Normalize composite key (lowercase, strip whitespace, phonetic matching optional). Keep first occurrence, log duplicates. Report dedup stats. |
| Hierarchical relationship preservation | Most scrapers produce flat CSVs. Preserving the region -> category -> listing hierarchy in JSON output (and as columns in CSV) demonstrates understanding of data modeling. | MEDIUM | Each record carries its full lineage (region name, category name, parent URL). JSON output nests naturally. CSV flattens with region/category columns. |
| Dry-run / preview mode | Run selectors against a single page without crawling the full site. Invaluable for config development and debugging. Shows thoughtful UX design. | LOW | Fetch one page per level, extract fields, print results to terminal. No output files, no state. Flag: `--dry-run` or `--preview`. |
| Adaptive delay based on response times | Instead of fixed delays, adjust pace based on server response time. Slow responses = back off more. Fast responses = safe to maintain pace. Similar to Scrapy's AutoThrottle. | MEDIUM | Track rolling average response time. If avg increases >50%, increase delay. If server returns 429, double delay for next N requests. Log delay adjustments. |
| Schema validation of config files | Validate the YAML/JSON config against a schema before crawling. Catch typos, missing required fields, and invalid selector syntax early. | LOW | Use jsonschema or pydantic to validate config. Provide clear error messages: "Level 2 is missing 'detail_url_selector'" rather than cryptic runtime errors 500 pages into a crawl. |
| Progress reporting during crawl | Real-time terminal output showing crawl progress: pages scraped, current depth level, error count, estimated time remaining. | LOW | Use rich or tqdm for terminal progress. Show: [Level 1: 5/12 regions] [Level 2: 45/~200 listings] [Level 3: 120 details] [Errors: 3] [ETA: ~15min]. |
| Multiple selector fallback per field | Define a priority list of selectors per field. If the first selector fails, try the next. Handles sites where the same data appears in different HTML structures across pages. | LOW | Config: `phone: ["span.phone", "div.contact-phone", "a[href^='tel:']"]`. Try in order, use first match. Log which selector matched for debugging. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that look good in a README but create problems in practice.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| CAPTCHA solving / bypass | "Handle all sites" completeness | Ethical and legal gray area. CAPTCHA services cost money. Anti-bot arms race you can't win. Signals the wrong intent for a portfolio project. | Document that the tool targets publicly accessible directories. If a site CAPTCHAs, it's signaling "don't scrape me" -- respect that. |
| Login / authentication support | "Scrape member-only directories" | Adds session management, cookie handling, credential storage complexity. Legal risk with protected content. Scope creep from the core value. | Out of scope by design. Document why: the tool demonstrates scraping public data, not bypassing access controls. |
| Proxy rotation / IP management | "Avoid getting blocked at scale" | Massive complexity (proxy pools, health checking, rotation logic). Signals aggressive crawling rather than polite scraping. Overkill for a portfolio batch tool. | Use polite delays and robots.txt compliance instead. If a site blocks you with reasonable delays, pick a different target site. |
| Stealth / anti-detection features | "Make Playwright undetectable" | Arms race with anti-bot systems. playwright-stealth patches leak detection vectors. CDP detection is advancing. Wrong signal for portfolio work. | Set a realistic User-Agent string. Don't try to be stealthy -- be polite. Portfolio projects should demonstrate ethical scraping, not evasion. |
| Real-time monitoring dashboard (web UI) | "Professional observability" | Massive scope creep. Building a web UI for a CLI batch tool adds React/Flask/WebSocket complexity that has nothing to do with scraping competence. | Terminal progress bar + JSON validation report + structured log files. These demonstrate the same skills without a separate application. |
| Database storage (PostgreSQL, MongoDB) | "Real data pipeline" | Adds database setup, schema migrations, connection management. CSV/JSON are portable and sufficient for the demo. Database integration is a different project. | CSV + JSON output covers all use cases. Mention in README that output is "pipeline-ready" for downstream database ingestion. |
| Distributed / multi-machine crawling | "Scale to millions of pages" | Requires message queues, work distribution, result aggregation. Entirely different architecture. A directory scraper doesn't need this scale. | Single-machine async with Playwright handles directory-scale crawling. Document scalability path in README if asked. |
| LLM-powered field extraction | "AI-powered scraping" | Adds LLM API dependency, cost, latency, and non-determinism. Trendy but wrong tool for structured directory data where CSS selectors work perfectly. | CSS/XPath selectors are deterministic, fast, and free. Mention LLM extraction as a future direction in README if desired. |
| Scheduled / continuous scraping (cron) | "Keep data fresh automatically" | Turns a batch tool into a service. Adds scheduling, state management, diff detection, notification complexity. Different product entirely. | Build as a batch tool that runs on demand. Users can wrap in cron themselves. Document this as intentional scope boundary. |

## Feature Dependencies

```
[Config-driven site definitions]
    |-- requires --> [CSS/XPath selector extraction]
    |-- requires --> [Multi-level navigation]
    |                    |-- requires --> [URL deduplication]
    |                    |-- requires --> [Pagination handling]
    |                    |-- enhances --> [Hierarchical relationship preservation]
    |
    |-- enables --> [Schema validation of config]
    |-- enables --> [Multiple selector fallback per field]
    |-- enables --> [Dry-run / preview mode]

[JS-rendered content handling (Playwright)]
    |-- enhances --> [Pagination handling] (click-to-load-more)
    |-- enhances --> [Multi-level navigation] (SPA-style directories)

[Data validation and cleaning]
    |-- requires --> [CSS/XPath selector extraction] (raw data to clean)
    |-- enables --> [Record deduplication] (needs normalized keys)
    |-- enables --> [Validation report] (needs validation results)

[Retry with exponential backoff]
    |-- enhances --> [HTTP error handling]
    |-- enhances --> [Checkpoint/resume] (retries feed into checkpoint state)

[Checkpoint/resume on interruption]
    |-- requires --> [URL deduplication] (needs visited-URL tracking)
    |-- requires --> [Structured logging] (needs to log resume point)

[CSV output] -- independent -- [JSON output]
    Both require --> [Data validation and cleaning]

[CLI interface]
    |-- enables --> [Dry-run / preview mode] (--dry-run flag)
    |-- enables --> [Progress reporting] (--verbose flag)
```

### Dependency Notes

- **Multi-level navigation requires URL deduplication:** Without dedup, the crawler will loop endlessly in cross-linked directory categories.
- **Config-driven definitions require selector extraction:** The config defines selectors; the extraction engine interprets them. These are designed together.
- **Checkpoint/resume requires URL deduplication tracking:** The visited-URL set IS the checkpoint state. Persisting it enables resume.
- **Record deduplication requires data validation:** Composite keys (name + address) only work after normalization (whitespace stripping, case normalization). Raw data will miss duplicates.
- **Dry-run requires config + CLI:** Preview mode applies config selectors to a single page, triggered by a CLI flag. Both must exist first.
- **Validation report requires data validation pipeline:** The report summarizes validation results -- field completeness, error rates, etc. Validation must run first.

## MVP Definition

### Launch With (v1)

Minimum viable scraper -- can navigate a real directory site and produce clean output.

- [ ] Config-driven site definitions (YAML) -- the architectural foundation; everything depends on this
- [ ] CSS selector extraction -- the core data extraction mechanism
- [ ] Multi-level navigation (3 depth levels) -- the defining feature of this project
- [ ] Pagination handling (next-page links at minimum) -- directories always paginate
- [ ] URL deduplication -- prevents infinite loops in cross-linked directories
- [ ] JS-rendered content via Playwright -- required for target site category (JS-heavy directories)
- [ ] Basic data cleaning (whitespace, HTML entities) -- minimum viable data quality
- [ ] CSV output with proper encoding -- universal output format
- [ ] Retry with exponential backoff -- minimum resilience
- [ ] HTTP error handling (429, 5xx, 404) -- graceful failure
- [ ] robots.txt compliance -- ethical baseline
- [ ] Configurable request delays -- polite crawling
- [ ] Structured logging -- debuggability
- [ ] CLI interface -- usability

### Add After Validation (v1.x)

Features that make the tool portfolio-impressive once core crawling works.

- [ ] JSON output with hierarchical structure -- once CSV proves the data model works
- [ ] Data validation pipeline (phone normalization, URL validation) -- once raw extraction is reliable
- [ ] Record deduplication by composite key -- once validation pipeline normalizes data
- [ ] Validation report with quality metrics -- once validation pipeline produces measurable results
- [ ] Checkpoint/resume on interruption -- once crawl state management is understood from v1 experience
- [ ] Dry-run / preview mode -- once config format is stabilized
- [ ] Progress reporting (rich/tqdm) -- polish for the demo
- [ ] Schema validation of config files -- catches config errors early

### Future Consideration (v2+)

Features to defer until the core is solid and demonstrated.

- [ ] Multiple selector fallback per field -- nice resilience, but adds config complexity
- [ ] Adaptive delay (auto-throttle) -- requires response time tracking infrastructure
- [ ] Hierarchical relationship preservation in JSON -- requires rethinking the data model
- [ ] NDJSON output for streaming pipelines -- niche use case
- [ ] Config inheritance (base config + site-specific overrides) -- only needed if supporting many sites

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-level navigation | HIGH | HIGH | P1 |
| Config-driven site definitions | HIGH | MEDIUM | P1 |
| JS-rendered content (Playwright) | HIGH | MEDIUM | P1 |
| CSS/XPath selector extraction | HIGH | LOW | P1 |
| Pagination handling | HIGH | MEDIUM | P1 |
| URL deduplication | HIGH | LOW | P1 |
| Retry with exponential backoff | HIGH | LOW | P1 |
| HTTP error handling | HIGH | LOW | P1 |
| robots.txt compliance | HIGH | LOW | P1 |
| Configurable request delays | HIGH | LOW | P1 |
| CSV output (proper encoding) | HIGH | LOW | P1 |
| Structured logging | HIGH | LOW | P1 |
| CLI interface | HIGH | LOW | P1 |
| Basic data cleaning | MEDIUM | LOW | P1 |
| JSON output (hierarchical) | HIGH | LOW | P2 |
| Data validation pipeline | HIGH | MEDIUM | P2 |
| Validation report | HIGH | MEDIUM | P2 |
| Record deduplication | MEDIUM | MEDIUM | P2 |
| Checkpoint/resume | HIGH | HIGH | P2 |
| Dry-run / preview mode | MEDIUM | LOW | P2 |
| Progress reporting | MEDIUM | LOW | P2 |
| Config schema validation | MEDIUM | LOW | P2 |
| Multiple selector fallback | LOW | LOW | P3 |
| Adaptive delay | LOW | MEDIUM | P3 |
| NDJSON output | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch -- the scraper doesn't work without these
- P2: Should have -- these make it portfolio-grade rather than tutorial-grade
- P3: Nice to have -- polish that can be added if time allows

## Competitor Feature Analysis

| Feature | Scrapy | Crawlee | Crawl4AI | Our Approach |
|---------|--------|---------|----------|--------------|
| Multi-level depth | Spider rules + callbacks | BFS/DFS strategies with max depth | Deep crawl with page limits | Config-defined levels with per-level selectors and pagination rules |
| JS rendering | Via scrapy-playwright plugin | Built-in Playwright/Puppeteer | Built-in browser crawling | Playwright as first-class citizen, not a plugin |
| Config-driven | Spider classes (code) | Code-based handlers | Code-based | YAML config files -- no code changes to add a new site |
| Checkpoint/resume | Job directory persistence | RequestQueue persistence | resume_state + on_state_change | JSON checkpoint file with visited URLs and queue state |
| Data validation | Item Pipeline with validators | Custom middleware | Post-processing | Built-in validation pipeline: phone, URL, email, whitespace |
| Output formats | CSV, JSON, XML via feed exports | Dataset storage | Markdown, JSON | CSV (RFC 4180 + BOM) and JSON (flat + hierarchical) |
| Progress reporting | Stats collector + log | Event system | Callbacks | Terminal progress bar with per-level counts and ETA |
| Anti-bot evasion | Middleware-based | Session rotation | Stealth mode | Polite crawling only -- ethical by design |

**Our differentiation:** Scrapy requires writing Python spider classes. Crawlee and Crawl4AI require code for each site. Our tool uses YAML config files that define a new directory site without touching code. This is a genuine architectural differentiator, not just a feature checkbox.

## Sources

- [Scrapy Architecture Overview](https://docs.scrapy.org/en/latest/topics/architecture.html) -- pipeline, middleware, and spider architecture patterns
- [Crawlee Request Retry and Error Recovery](https://webscraping.ai/faq/crawlee/how-does-crawlee-handle-request-retries-and-error-recovery) -- checkpoint and resume patterns
- [Crawlee Resuming Paused Crawl](https://crawlee.dev/python/docs/examples/resuming-paused-crawl) -- RequestQueue persistence for resume
- [Scrapling Framework](https://github.com/D4Vinci/Scrapling) -- checkpoint with Ctrl+C graceful pause
- [Crawl4AI Deep Crawl](https://github.com/unclecode/crawl4ai) -- resume_state and BFS crawling
- [ScrapingBee Web Scraping Best Practices](https://www.scrapingbee.com/blog/web-scraping-best-practices/) -- rate limiting, error handling, polite crawling
- [ZenRows Web Scraping Best Practices](https://www.zenrows.com/blog/web-scraping-best-practices) -- production scraper patterns
- [Scrapfly Data Quality Guide](https://scrapfly.io/blog/posts/how-to-ensure-web-scrapped-data-quality) -- validation with Cerberus and Pydantic
- [robots.txt Scraping Compliance Guide](https://www.promptcloud.com/blog/robots-txt-scraping-compliance-guide/) -- ethical crawling standards
- [CSV vs JSON for Scraping](https://infatica.io/blog/json-csv-xlsx-overview/) -- output format tradeoffs
- [Crawl4AI Monitoring and Logging Guide](https://www.crawl4.com/blog/crawl4ai-monitoring-logging-a-production-ready-guide) -- structured logging for scrapers
- [Dynamically Configurable Scrapy Spider](https://www.cyberangles.org/blog/using-one-scrapy-spider-for-several-websites/) -- config-driven multi-site pattern
- [Scrapit YAML-driven Scraper](http://scrapit.space/) -- YAML config pattern for web scraping
- [LLM-Powered Data Normalization](https://scrapingant.com/blog/llm-powered-data-normalization-cleaning-scraped-data) -- why LLMs are overkill when selectors work

---
*Feature research for: multi-level directory scraper*
*Researched: 2026-03-13*
