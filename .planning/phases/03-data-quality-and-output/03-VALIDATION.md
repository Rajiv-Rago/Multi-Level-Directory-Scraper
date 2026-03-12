---
phase: 3
slug: data-quality-and-output
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 creates |
| **Quick run command** | `pytest tests/test_pipeline/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pipeline/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | ALL | setup | `pytest --co -q` | No -- W0 | pending |
| 03-01-02 | 01 | 1 | VAL-04 | unit | `pytest tests/test_pipeline/test_cleaning.py -x` | No -- W0 | pending |
| 03-01-03 | 01 | 1 | VAL-01 | unit | `pytest tests/test_pipeline/test_phone.py -x` | No -- W0 | pending |
| 03-01-04 | 01 | 1 | VAL-02 | unit | `pytest tests/test_pipeline/test_urls.py -x` | No -- W0 | pending |
| 03-01-05 | 01 | 1 | VAL-03 | unit | `pytest tests/test_pipeline/test_dedup.py -x` | No -- W0 | pending |
| 03-02-01 | 02 | 2 | VAL-06, OUT-01 | unit | `pytest tests/test_export/test_csv.py -x` | No -- W0 | pending |
| 03-02-02 | 02 | 2 | OUT-02 | unit | `pytest tests/test_export/test_json.py -x` | No -- W0 | pending |
| 03-02-03 | 02 | 2 | VAL-05, OUT-03 | integration | `pytest tests/test_pipeline/test_report.py -x` | No -- W0 | pending |
| 03-02-04 | 02 | 2 | ALL | integration | `pytest tests/test_pipeline/test_pipeline_integration.py -x` | No -- W0 | pending |

*Status: pending -- all tests created as part of Wave 0/implementation*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` -- pytest config with `[tool.pytest.ini_options]`
- [ ] `tests/conftest.py` -- shared fixtures (sample records, sample config, tmp output dir)
- [ ] `tests/test_pipeline/conftest.py` -- pipeline-specific fixtures
- [ ] `tests/test_pipeline/test_cleaning.py` -- stubs for VAL-04
- [ ] `tests/test_pipeline/test_phone.py` -- stubs for VAL-01
- [ ] `tests/test_pipeline/test_urls.py` -- stubs for VAL-02
- [ ] `tests/test_pipeline/test_dedup.py` -- stubs for VAL-03
- [ ] `tests/test_pipeline/test_report.py` -- stubs for VAL-05, OUT-03
- [ ] `tests/test_export/test_csv.py` -- stubs for VAL-06, OUT-01
- [ ] `tests/test_export/test_json.py` -- stubs for OUT-02
- [ ] `tests/test_pipeline/test_pipeline_integration.py` -- end-to-end pipeline test
- [ ] `pip install pytest phonenumbers pydantic` -- dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSV opens in Excel without encoding artifacts | VAL-06 | Requires actual Excel/Sheets UI | Open `data.csv` in Excel and Google Sheets; verify headers display correctly, accented characters render, no BOM visible as characters |
| Validation report is "impressive" for portfolio | OUT-03 | Subjective quality | Review `validation_report.json` structure; verify >95% completeness is prominently displayed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
