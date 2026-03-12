---
phase: 2
slug: crawl-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pyproject.toml (test config section) |
| **Quick run command** | `pytest tests/unit/ -x -q` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | NAV-04 | unit | `pytest tests/unit/test_frontier.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | NAV-04 | unit | `pytest tests/unit/test_url_normalize.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | JS-01, JS-03 | unit | `pytest tests/unit/test_fetcher.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | EXT-01, EXT-02, EXT-05 | unit | `pytest tests/unit/test_extractor.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | RES-01, RES-02 | unit | `pytest tests/unit/test_retry.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | NAV-03, JS-02 | unit | `pytest tests/unit/test_pagination.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | EXT-03 | unit | `pytest tests/unit/test_context_propagation.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | NAV-01, NAV-02, NAV-05 | integration | `pytest tests/integration/test_orchestrator.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_frontier.py` — stubs for NAV-04 (URL dedup, normalization)
- [ ] `tests/unit/test_fetcher.py` — stubs for JS-01, JS-03 (wait_for_selector, timeout)
- [ ] `tests/unit/test_extractor.py` — stubs for EXT-01, EXT-02, EXT-05 (field extraction, fallback selectors)
- [ ] `tests/unit/test_retry.py` — stubs for RES-01, RES-02 (429 backoff, 5xx retry)
- [ ] `tests/unit/test_pagination.py` — stubs for NAV-03, JS-02 (next_page, load_more, infinite_scroll)
- [ ] `tests/unit/test_context_propagation.py` — stubs for EXT-03 (ancestor metadata)
- [ ] `tests/unit/test_url_normalize.py` — stubs for URL normalization edge cases
- [ ] `tests/integration/test_orchestrator.py` — stubs for full traversal against local test server
- [ ] `tests/conftest.py` — shared fixtures (sample HTML, config objects)
- [ ] pytest + pytest-asyncio installed in dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real site traversal | NAV-01, NAV-02 | Depends on external site availability | Run against example config YAML targeting a real directory; verify records extracted from all 3 levels |
| Polite delay enforcement | RES-04 (Phase 1) | Timing-based verification unreliable in CI | Observe log timestamps between requests; verify 1-3s gaps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
