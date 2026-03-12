---
plan: 02-01
phase: 02-crawl-engine
status: complete
started: 2026-03-13
completed: 2026-03-13
---

## What Was Built

URL frontier with deduplication, normalization, and per-level queues with ancestor tracking. Dual-mode fetcher supporting both Playwright (JS-rendered) and httpx (static) pages.

## Key Files

### Created
- `src/scraper/frontier.py` — URL frontier: normalize_url(), FrontierItem dataclass, URLFrontier class with dedup/per-level queues
- `src/scraper/fetcher.py` — PlaywrightFetcher (wait_selector/networkidle/timeout handling), HttpxFetcher (status code handling), RateLimitError/ServerError exceptions
- `tests/unit/test_url_normalize.py` — 9 normalization tests
- `tests/unit/test_frontier.py` — 12 frontier tests
- `tests/unit/test_fetcher.py` — 9 fetcher tests

### Modified
- `pyproject.toml` — Added playwright, tenacity, pytest-asyncio dependencies

## Test Results

30 new tests, all passing. 63 total (including Phase 1), no regressions.

## Decisions

- URL normalization strips trailing slashes (except root "/"), lowercases scheme/host, sorts query params, removes fragments, removes default ports
- FrontierItem carries ancestor metadata for context propagation to detail records
- PlaywrightFetcher returns partial HTML on timeout (logs warning, doesn't crash)
- HttpxFetcher raises typed exceptions (RateLimitError, ServerError) for retry integration

## Self-Check: PASSED
