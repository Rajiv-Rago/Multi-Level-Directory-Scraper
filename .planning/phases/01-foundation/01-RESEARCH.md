# Phase 1: Foundation - Research

**Researched:** 2026-03-13
**Question:** What do I need to know to PLAN this phase well?

## Phase Scope

Phase 1 delivers the project skeleton: config loading (YAML), CLI with overrides, config validation with clear errors, dry-run mode, structured logging, robots.txt compliance, and randomized request delays. Requirements: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, RES-03, RES-04, RES-06.

## Technical Findings

### 1. Project Structure

The research recommends `src/scraper/` flat package structure. Phase 1 modules:

```
src/scraper/
  __init__.py
  __main__.py        # python -m scraper support
  cli.py             # Typer app, entry point
  config.py          # Pydantic models + YAML loading
  logging.py         # structlog configuration
  politeness.py      # robots.txt + delay controller
```

Additional files:
```
pyproject.toml       # uv/pip project config with entry point
configs/
  example.yaml       # Annotated example config
tests/
  conftest.py
  test_config.py
  test_cli.py
  test_logging.py
  test_politeness.py
```

Entry point in pyproject.toml: `[project.scripts] scraper = "scraper.cli:app"` so users invoke `scraper <config> [--flags]`.

### 2. Config Models (Pydantic v2)

The config has two top-level sections: `site` and `levels`.

```yaml
site:
  name: "Example Directory"
  base_url: "https://example.com/directory"
  output_dir: "./output"
  request_delay:
    min: 1.0
    max: 3.0
  max_pages: null  # unlimited by default
  log_level: "info"

levels:
  - name: "regions"
    depth: 0
    link_selector: "a.region-link"
    pagination:
      type: "next_button"
      selector: "a.next-page"
    fields:
      - name: "region_name"
        selector: "h1.region-title"
```

Pydantic model hierarchy:
- `RequestDelayConfig(BaseModel, frozen=True)`: min, max with `model_validator` ensuring min <= max
- `PaginationConfig(BaseModel, frozen=True)`: type (enum: next_button, load_more, infinite_scroll, none), selector
- `FieldMapping(BaseModel, frozen=True)`: name, selector (CSS), attribute (optional, default "text"), default (optional)
- `LevelConfig(BaseModel, frozen=True)`: name, depth, link_selector, pagination (optional), fields (list of FieldMapping)
- `SiteConfig(BaseModel, frozen=True)`: name, base_url (HttpUrl), output_dir, request_delay, max_pages, log_level
- `ScrapeConfig(BaseModel, frozen=True)`: site (SiteConfig), levels (list of LevelConfig)

Key Pydantic v2 patterns:
- Use `frozen=True` in `model_config = ConfigDict(frozen=True)` for immutability
- `field_validator` for per-field validation (CSS selector syntax check, URL format)
- `model_validator(mode='after')` for cross-field validation (min <= max delay, unique level names, sequential depths)
- Validation errors are field-level and actionable via Pydantic's built-in error formatting
- Custom error messages via `ValueError` in validators

### 3. CLI Design (Typer)

Single command, no subcommands. Config path is positional argument.

```python
app = typer.Typer()

@app.command()
def main(
    config_path: Annotated[Path, typer.Argument(help="Path to YAML config file")],
    output_dir: Annotated[Optional[str], typer.Option("--output-dir")] = None,
    delay_min: Annotated[Optional[float], typer.Option("--delay-min")] = None,
    delay_max: Annotated[Optional[float], typer.Option("--delay-max")] = None,
    max_pages: Annotated[Optional[int], typer.Option("--max-pages")] = None,
    log_level: Annotated[Optional[str], typer.Option("--log-level")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
):
```

Override application: CLI args that are not None override corresponding config values. Build a dict of overrides, apply after config loading.

Exit codes: 0 = success, 1 = config validation error, 2 = runtime error. Use `raise typer.Exit(code=1)` for config errors.

### 4. Structured Logging (structlog)

Dual-output setup using `logging.config.dictConfig`:
- **Console**: `structlog.dev.ConsoleRenderer(colors=True)` for pretty colored output
- **File**: `structlog.processors.JSONRenderer()` for machine-parseable JSON lines

Processor chain:
1. `structlog.stdlib.add_log_level` — adds level name
2. `structlog.processors.TimeStamper(fmt="iso")` — ISO 8601 timestamps
3. `structlog.processors.StackInfoRenderer()` — stack traces
4. `structlog.processors.format_exc_info` — exception formatting
5. `structlog.processors.UnicodeDecoder()` — bytes to str
6. `structlog.stdlib.ProcessorFormatter.wrap_for_formatter` — handoff to stdlib

Use `structlog.stdlib.BoundLogger` as wrapper class. The `BoundLogger` API mirrors `logging.Logger` so `log.info("event", url=url, level_name=name)` works naturally.

Log file goes to `{output_dir}/scrape.log` as JSON lines. In dry-run mode, no log file is written.

Log level controlled by config `site.log_level` with CLI override `--log-level`.

### 5. robots.txt Compliance

`urllib.robotparser.RobotFileParser` from stdlib:
- Fetch from `{base_url}/robots.txt` using httpx
- `rp.read()` or `rp.parse(lines)` to load rules
- `rp.can_fetch(user_agent, url)` to check each URL
- `rp.crawl_delay(user_agent)` for Crawl-delay directive

**Caveat**: stdlib `robotparser` does NOT support `Crawl-delay`. Need to parse it manually from the raw robots.txt text, or use the `protego` library. For Phase 1, manual parsing of Crawl-delay from raw text is simplest -- read robots.txt as text, regex for `Crawl-delay: (\d+)`, use that value if present.

Cache: fetch once at startup, store in a `PolitenessController` class that holds the parser + delay config.

If robots.txt fetch fails (404, network error): log warning, proceed with assumption that all URLs are allowed.

### 6. Request Delays

`random.uniform(min, max)` between each request. The `PolitenessController` handles:
- Storing min/max from config (after CLI overrides)
- Checking robots.txt Crawl-delay: if present and > config min, use robots.txt value as min
- `async def wait()` method that sleeps for `random.uniform(effective_min, max)`
- `def is_allowed(url: str) -> bool` that checks robots.txt

### 7. Dry-Run Mode

When `--dry-run` is active:
1. Load and validate config fully
2. For each configured level, fetch ONE page (the base_url for level 0, first link for deeper levels)
3. Apply field selectors against the fetched page
4. Display results in a readable table (field name, selector, value found or "NOT FOUND")
5. Do NOT write output files or log files
6. Do NOT follow pagination or next-level links
7. Exit 0 if all levels extract at least one field, exit 1 if issues found

Table output: Use `rich.table.Table` for formatted terminal output (rich is installed as a structlog dev dependency for pretty console rendering). Alternatively, plain text formatting is acceptable per context decisions.

**Note**: Dry-run requires making HTTP requests. In Phase 1, use httpx for fetching pages (not Playwright -- that's Phase 2). Dry-run validates config + selectors work against static HTML. If the target site requires JS rendering, dry-run will report "NOT FOUND" for JS-rendered content, which is expected and should be noted in output.

### 8. Testing Strategy

- **test_config.py**: Valid config loading, missing required fields, bad types, cross-field validation (min > max delay), immutability
- **test_cli.py**: Config path argument, each CLI override, dry-run flag, exit codes. Use `typer.testing.CliRunner`
- **test_logging.py**: Log output contains expected fields (timestamp, level, event), JSON format in file mode, console format in TTY mode
- **test_politeness.py**: robots.txt parsing, Crawl-delay extraction, URL allow/disallow, delay calculation, robots.txt fetch failure handling. Use `respx` to mock httpx calls

Fixtures: sample YAML config files in `tests/fixtures/` directory or as pytest fixtures using `tmp_path`.

## Validation Architecture

### Observable Behaviors (from requirements)

| Req ID | Observable Behavior | How to Verify |
|--------|-------------------|---------------|
| CFG-01 | Config loads from YAML with all sections | Load example.yaml, assert all fields accessible on model |
| CFG-02 | CLI args override config values | Run with --delay-min 5.0, assert config.site.request_delay.min == 5.0 |
| CFG-03 | Invalid config produces clear error | Load bad config, assert error message mentions specific field and issue |
| CFG-04 | Dry-run fetches one page per level, prints table, no output files | Run --dry-run, check stdout for table, check no files written |
| CFG-05 | Terminal shows progress during crawl | Log output includes level name, page count (basic in Phase 1) |
| RES-03 | robots.txt checked before requests | Mock robots.txt with Disallow, verify URL skipped with log message |
| RES-04 | Random delay between requests within configured range | Time multiple delays, assert all within [min, max] range |
| RES-06 | All events logged with timestamp, URL, event type | Parse JSON log lines, assert required fields present |

### Test Boundaries

- Config validation: unit tests with valid/invalid YAML fixtures
- CLI: integration tests with CliRunner
- Logging: unit tests capturing log output
- Politeness: unit tests with mocked HTTP (respx)
- Dry-run: integration test with mocked HTTP responses returning sample HTML

## Dependencies and Risks

| Risk | Mitigation |
|------|------------|
| stdlib robotparser doesn't support Crawl-delay | Manual parsing from raw text, or upgrade to protego later |
| Dry-run needs real HTTP but no Playwright yet | Use httpx for dry-run page fetching; note JS limitation in output |
| structlog + stdlib logging integration complexity | Follow the dictConfig pattern from structlog docs exactly |
| Config schema may need revision in Phase 2 | frozen=True prevents mutation; new fields added via model inheritance or new optional fields |

## Plan Decomposition Guidance

Natural split into two plans:
1. **Plan 01-01: Project skeleton + config + CLI + logging** — The core infrastructure. Everything that doesn't touch the network. Config models, CLI parsing, logging setup, project structure, pyproject.toml.
2. **Plan 01-02: Politeness controller + dry-run mode** — Network-touching code. robots.txt, delays, dry-run page fetching and display. Depends on 01-01 for config models and logging.

This split allows wave 1 (01-01) to be fully testable without mocking HTTP, and wave 2 (01-02) to focus on the HTTP-dependent behavior.

## RESEARCH COMPLETE

Research covers all 8 Phase 1 requirements with implementation patterns, testing strategy, and plan decomposition guidance.
