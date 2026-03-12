---
phase: 4
slug: resilience-and-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml or pytest.ini (from Phase 1) |
| **Quick run command** | `pytest tests/test_checkpoint.py tests/test_signals.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_checkpoint.py tests/test_signals.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | RES-07 | unit | `pytest tests/test_checkpoint.py::test_save_load_roundtrip -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | RES-07 | unit | `pytest tests/test_checkpoint.py::test_atomic_write -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | RES-05 | integration | `pytest tests/test_signals.py::test_sigint_saves_partial -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | RES-07 | integration | `pytest tests/test_signals.py::test_sigint_saves_checkpoint -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | RES-08 | integration | `pytest tests/test_checkpoint.py::test_resume_skips_visited -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | RES-08 | unit | `pytest tests/test_checkpoint.py::test_config_mismatch_warning -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | DOC-01 | manual | n/a | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_checkpoint.py` — stubs for RES-07, RES-08 (checkpoint save/load, atomic write, resume, config mismatch)
- [ ] `tests/test_signals.py` — stubs for RES-05, RES-07 (signal handling, graceful shutdown, partial result save)
- [ ] `tests/conftest.py` — shared fixtures (mock crawl state, temp output dir, mock server)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README contains all required sections | DOC-01 | Content quality requires human review | Verify README has: problem statement, approach, data quality, resilience with log examples, sample output, setup instructions. Verify setup works in <5 min. |
| README log snippets show real resilience | DOC-01 | Authenticity of log examples | Verify log snippets are from actual scraper runs, not fabricated |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
