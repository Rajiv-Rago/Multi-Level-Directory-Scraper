---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CFG-01 | unit | `uv run pytest tests/test_config.py -k "test_valid_config"` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CFG-03 | unit | `uv run pytest tests/test_config.py -k "test_invalid"` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CFG-02 | unit | `uv run pytest tests/test_cli.py -k "test_override"` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | RES-06 | unit | `uv run pytest tests/test_logging.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | RES-03 | unit | `uv run pytest tests/test_politeness.py -k "test_robots"` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | RES-04 | unit | `uv run pytest tests/test_politeness.py -k "test_delay"` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 2 | CFG-04 | integration | `uv run pytest tests/test_cli.py -k "test_dry_run"` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 2 | CFG-05 | integration | `uv run pytest tests/test_cli.py -k "test_progress"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (sample config dicts, tmp_path configs)
- [ ] `tests/test_config.py` — stubs for CFG-01, CFG-03
- [ ] `tests/test_cli.py` — stubs for CFG-02, CFG-04, CFG-05
- [ ] `tests/test_logging.py` — stubs for RES-06
- [ ] `tests/test_politeness.py` — stubs for RES-03, RES-04
- [ ] pytest + respx installation via `uv add --dev pytest respx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Colored console log output | RES-06 | Terminal color rendering cannot be asserted in CI | Run `scraper example.yaml --log-level debug`, visually confirm colored output |
| Dry-run table readability | CFG-04 | Table formatting is visual | Run `scraper example.yaml --dry-run`, confirm table is aligned and readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
