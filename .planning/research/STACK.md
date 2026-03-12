# Technology Stack

**Project:** Multi-Level Directory Scraper
**Researched:** 2026-03-13

## Recommended Stack

### Language & Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | Ecosystem dominance in scraping; async/await mature; type hints standard. 3.12 for performance improvements and better error messages. 3.13 acceptable but 3.12 has wider library compatibility. | HIGH |

### Browser Automation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Playwright | 1.58.0 | JS rendering, navigation, dynamic content | Auto-wait eliminates manual sleep/polling. Native async API fits concurrent scraping. Built-in selectors for DOM querying. Handles infinite scroll, click-to-load, and SPAs. Actively maintained by Microsoft with monthly releases. | HIGH |

Playwright is the correct choice over Selenium. Selenium requires explicit waits everywhere, has no built-in auto-wait, and its Python async story is weaker. Playwright's `page.wait_for_selector()`, `page.wait_for_load_state("networkidle")`, and auto-wait on actions directly address the spec's BEH-JS-01 through BEH-JS-03 requirements.

### HTML Parsing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| BeautifulSoup4 | 4.14.3 | Parse rendered HTML from Playwright | Forgiving parser that handles malformed HTML gracefully. CSS selector support via `.select()`. Huge ecosystem of tutorials and examples (portfolio visibility). | HIGH |
| lxml | 6.0.2 | Parser backend for BS4 | Use `lxml` as the BS4 parser backend (`BeautifulSoup(html, 'lxml')`) for 5-10x speed over the default `html.parser`. C-based, handles large DOMs efficiently. | HIGH |

**Pattern:** Playwright renders the page and returns `page.content()` as HTML string. BeautifulSoup+lxml parses the HTML for extraction. This separates the rendering concern (Playwright) from the parsing concern (BS4) cleanly.

**Why not Playwright's built-in selectors for all extraction?** Playwright's `query_selector_all` works but is slower for bulk extraction because each call crosses the Python-to-browser bridge. Getting the full HTML once and parsing locally with BS4+lxml is faster for pages with many fields.

**Why not selectolax?** Selectolax is 2-5x faster than BS4+lxml but has a smaller community, fewer tutorials, and less forgiving error handling. For a portfolio project processing hundreds to low-thousands of pages (not millions), BS4's developer experience and recognizability outweigh selectolax's raw speed.

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | 0.28.1 | robots.txt fetching, static page fallback, API endpoint discovery | Native async/sync dual API. HTTP/2 support. Drop-in requests replacement with `httpx.get()`. Will use for fetching robots.txt and any non-JS pages discovered during crawling. | HIGH |

**Why not `requests`?** httpx provides async support that integrates with Playwright's async event loop. Using `requests` alongside Playwright's async API would require threading or `run_in_executor`, adding unnecessary complexity.

### Data Processing & Output

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pandas | 3.0.1 | CSV/JSON export, deduplication, data cleaning | DataFrame operations for dedup (`drop_duplicates`), CSV export with encoding control, JSON export with orient options. pandas 3.0 defaults to PyArrow-backed strings, which handles Unicode better. | HIGH |
| Pydantic | 2.12.5 | Schema validation, data models | Define record schemas as Pydantic models. Validates extracted data at ingestion time (not just at export). Rust-based core is fast. Emits JSON Schema for the validation report. | HIGH |

**Why Pydantic over ad-hoc validation?** The spec requires phone normalization, URL validation, whitespace stripping, and HTML entity decoding (BEH-VAL-01 through BEH-VAL-04). Pydantic validators handle all of these declaratively. A `BusinessRecord` model with field validators is cleaner and more testable than scattered validation functions.

### Phone Number Handling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| phonenumbers | 8.13.x | Phone parsing, validation, E.164 normalization | Python port of Google's libphonenumber. Parses any format, validates against country rules, formats to E.164. Industry standard -- no reason to build custom. | HIGH |

### Configuration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyYAML | 6.0.2 | YAML config file parsing | Simple, well-known, sufficient for read-only config loading. The project only reads configs, never writes them back, so ruamel.yaml's round-trip preservation adds no value. | HIGH |

**Why PyYAML over ruamel.yaml?** ruamel.yaml preserves comments on round-trip (load-modify-save). This project only loads config, never modifies it programmatically. PyYAML is simpler, has wider community recognition, and has no downsides for read-only use.

### CLI Interface

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Typer | 0.24.1 | CLI argument parsing, help generation | Type-hint-driven CLI definitions. Auto-generates `--help`. Built on Click but with less boilerplate. Clean syntax for a portfolio project. | HIGH |

**Why Typer over Click/argparse?** Typer produces cleaner code with Python type hints instead of decorators. For a portfolio project, the code reads better. Click is the underlying engine so there's no reliability tradeoff.

### Retry & Resilience

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| tenacity | 9.1.4 | Exponential backoff, retry logic | Decorator-based retry with configurable wait strategies (`wait_exponential`), stop conditions (`stop_after_attempt`), and retry filters (`retry_if_exception_type`). Directly addresses BEH-RES-01 and BEH-RES-02. | HIGH |

**Why tenacity over hand-rolled retry loops?** Tenacity's decorator approach keeps retry logic separate from business logic. `@retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(3))` is more readable and testable than nested try/except/sleep loops.

### Logging

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| structlog | 25.5.0 | Structured logging with context | Key-value structured logs. Bind context (current URL, depth level) once, carry through all subsequent log calls. JSON output for machine parsing, pretty console output for development. Directly supports BEH-RES-06 requirement for timestamps + URLs + error types. | HIGH |

**Why structlog over stdlib logging?** stdlib logging can do structured output with extra effort, but structlog makes it natural. `log.bind(url=url, depth=depth).info("extracting")` produces `{"event": "extracting", "url": "...", "depth": 2, "timestamp": "..."}` with zero formatting boilerplate.

### robots.txt Compliance

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| urllib.robotparser | stdlib | robots.txt parsing | Built into Python stdlib. Sufficient for basic robots.txt compliance (BEH-RES-03). No external dependency needed. | MEDIUM |

**Caveat:** urllib.robotparser is based on the 1994 spec, not RFC 9309 (2022). For this portfolio project's scope (respecting Disallow directives), it's adequate. If advanced directives like Crawl-delay parsing from robots.txt are needed, consider `protego` (pip install protego) as an upgrade -- it's RFC 9309 compliant.

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | 8.x | Test framework | Standard Python testing. Fixtures for test data. Parameterize for testing multiple selectors. | HIGH |
| pytest-asyncio | 0.24.x | Async test support | Required for testing async Playwright and httpx code. | HIGH |
| pytest-playwright | 0.6.x | Playwright test fixtures | Provides `page`, `browser`, `context` fixtures. Handles browser lifecycle in tests. | MEDIUM |
| responses / respx | latest | HTTP mocking | `respx` for mocking httpx calls in tests. | MEDIUM |

### Dev Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | latest | Linting + formatting | Replaces flake8 + black + isort. Single tool, extremely fast (Rust-based). De facto standard in 2025+. | HIGH |
| mypy | latest | Type checking | Pydantic models + type hints throughout. Catches data shape bugs at dev time. | MEDIUM |
| uv | latest | Package management | Faster pip replacement. Manages virtualenvs. Becoming the standard Python package tool. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Browser automation | Playwright | Selenium | No auto-wait, weaker async, slower, more boilerplate |
| Browser automation | Playwright | Scrapy + Splash | Splash is a separate service to run; Playwright is simpler for this scope |
| HTTP client | httpx | requests | No async support; would fight Playwright's event loop |
| HTTP client | httpx | aiohttp | Lower-level API, more boilerplate; httpx has sync+async in one package |
| HTML parsing | BS4 + lxml | selectolax | Faster but less known; portfolio recognition matters |
| HTML parsing | BS4 + lxml | Parsel (Scrapy) | Good library but pulls in Scrapy ecosystem baggage |
| Data validation | Pydantic | marshmallow | Slower, less Pythonic, no type-hint integration |
| Data validation | Pydantic | attrs + cattrs | More manual validation setup; Pydantic has better JSON Schema support |
| Config | PyYAML | TOML (tomllib) | YAML better for deeply nested config (selectors, URL patterns) |
| Config | PyYAML | JSON config | No comments allowed in JSON; YAML supports inline documentation |
| CLI | Typer | Click | More boilerplate for same result |
| CLI | Typer | argparse | Verbose, no auto-help generation from type hints |
| Retry | tenacity | backoff | tenacity more actively maintained, richer API |
| Logging | structlog | loguru | loguru is simpler but structlog's bound context fits scraping workflow better |
| Scraping framework | Custom | Scrapy | Scrapy is a full framework with its own event loop, project structure, and middleware stack. For a 3-level directory scraper, it's overengineered. Custom code with Playwright + BS4 is more transparent for a portfolio piece where the architecture itself demonstrates skill. |

## Full Dependency List

```bash
# Core dependencies
pip install playwright beautifulsoup4 lxml httpx pandas pydantic phonenumbers pyyaml typer tenacity structlog

# Post-install: download browser binaries
playwright install chromium

# Dev dependencies
pip install -D pytest pytest-asyncio pytest-playwright respx ruff mypy
```

### pyproject.toml Dependencies (for uv/pip)

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.58.0",
    "beautifulsoup4>=4.14.0",
    "lxml>=6.0.0",
    "httpx>=0.28.0",
    "pandas>=3.0.0",
    "pydantic>=2.12.0",
    "phonenumbers>=8.13.0",
    "pyyaml>=6.0",
    "typer>=0.24.0",
    "tenacity>=9.1.0",
    "structlog>=25.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "pytest-playwright>=0.6.0",
    "respx>=0.22.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
]
```

## Architecture Implications

The stack naturally suggests this data flow:

```
CLI (Typer) -> Config (PyYAML) -> Crawler (Playwright async)
    -> Page HTML -> Parser (BS4 + lxml) -> Raw Records
    -> Validator (Pydantic) -> Clean Records
    -> Exporter (pandas) -> CSV + JSON + Report
```

Key integration points:
- **Playwright + asyncio**: All browser operations are async. The crawler loop uses `async for` patterns.
- **Playwright -> BS4**: `html = await page.content()` then `soup = BeautifulSoup(html, 'lxml')`. Clean handoff.
- **BS4 -> Pydantic**: Extract dict from soup, pass to `BusinessRecord(**data)`. Validation happens at construction.
- **Pydantic -> pandas**: `pd.DataFrame([record.model_dump() for record in records])`. Direct serialization.
- **tenacity wraps Playwright calls**: `@retry` decorator on the page-fetching function, not on individual selectors.
- **structlog binds context**: Bind URL and depth at the start of each page visit; all downstream logs inherit context.

## Sources

- [Playwright PyPI](https://pypi.org/project/playwright/) - Version 1.58.0
- [Playwright Python Release Notes](https://playwright.dev/python/docs/release-notes) - Release history
- [Playwright Auto-waiting Docs](https://playwright.dev/python/docs/actionability) - Auto-wait behavior
- [beautifulsoup4 PyPI](https://pypi.org/project/beautifulsoup4/) - Version 4.14.3
- [httpx PyPI](https://pypi.org/project/httpx/) - Version 0.28.1
- [HTTPX Official Site](https://www.python-httpx.org/) - Feature documentation
- [pandas Release Notes](https://pandas.pydata.org/docs/whatsnew/index.html) - Version 3.0.1
- [Pydantic Docs](https://docs.pydantic.dev/latest/) - Version 2.12.5
- [phonenumbers PyPI](https://pypi.org/project/phonenumbers/) - Google libphonenumber port
- [Typer PyPI](https://pypi.org/project/typer/) - Version 0.24.1
- [tenacity PyPI](https://pypi.org/project/tenacity/) - Version 9.1.4
- [structlog Docs](https://www.structlog.org/) - Version 25.5.0
- [lxml PyPI](https://pypi.org/project/lxml/) - Version 6.0.2
- [HTTPX vs Requests vs AIOHTTP](https://oxylabs.io/blog/httpx-vs-requests-vs-aiohttp) - Comparison
- [Python Web Scraping Libraries 2025](https://scrape.do/blog/python-web-scraping-library/) - Ecosystem overview
- [Selectolax vs BS4 vs lxml](https://medium.com/@yahyamrafe202/in-depth-comparison-of-web-scraping-parsers-lxml-beautifulsoup-and-selectolax-4f268ddea8df) - Parser performance comparison
