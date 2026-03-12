# Phase 4: Resilience and Documentation - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

The scraper survives interruptions (SIGINT/SIGTERM) without losing work, can resume from where it left off, and the project is documented with a portfolio-quality README. This phase adds checkpoint/resume on top of the working data pipeline from Phases 1-3, plus final documentation.

Requirements: RES-05, RES-07, RES-08, DOC-01

</domain>

<decisions>
## Implementation Decisions

### Checkpoint state persistence
- Save crawl state on SIGINT/SIGTERM and periodically during crawl (RES-07)
- State includes: visited URLs set, pending URL queue, current progress counters, extracted records count
- Partial results already extracted are saved to disk immediately on interruption (RES-05)
- Checkpoint file lives alongside output files in the output directory (co-located with run artifacts)
- JSON format for checkpoint file — human-readable, debuggable, no binary serialization

### Resume behavior
- On restart, the scraper detects a checkpoint file and offers to resume (RES-08)
- CLI flag `--resume` to explicitly resume from checkpoint without interactive prompt
- If checkpoint is from a different config (different base URL or selectors), warn and require `--force` to override
- Stale checkpoint handling: checkpoints older than 24 hours trigger a warning but still allow resume
- On successful completion, the checkpoint file is cleaned up (deleted)

### Signal handling
- Register handlers for both SIGINT (Ctrl+C) and SIGTERM
- On first signal: graceful shutdown — finish current page, save state, save partial results, exit
- On second signal (impatient user): immediate shutdown — save whatever state is available, exit
- Log the interruption event clearly so the user knows state was saved

### Periodic checkpointing
- Save checkpoint after every N pages (configurable, default every 50 pages)
- Also save after completing each navigation level (all regions done, all listings done, etc.)
- Atomic writes — write to temp file then rename to avoid corrupt checkpoint on crash

### Partial result persistence (RES-05)
- Records extracted so far are flushed to output files on interruption
- Output files are marked as partial (e.g., filename includes "partial" or a metadata field indicates incomplete run)
- On resume, partial output is continued (appended to), not overwritten

### README documentation (DOC-01)
- Sections: Problem statement, Approach and key decisions, Data quality achieved, Resilience (with log examples), Sample output, Setup instructions
- Setup must be runnable in under 5 minutes
- Include truncated sample of CSV and JSON output so reviewers see results without running
- Include real log output snippets showing resilience in action (retry, recovery, checkpoint)
- Tone: technical but accessible — written for hiring managers and senior engineers reviewing a portfolio

### Claude's Discretion
- Exact checkpoint file schema and field names
- Periodic checkpoint interval tuning (50 pages is a starting point)
- README formatting details (badges, table of contents, section ordering beyond required sections)
- Whether to include architecture diagram in README
- How to mark output files as partial vs complete

</decisions>

<specifics>
## Specific Ideas

- From spec section 6: "README is as important as the code" — treat documentation as a first-class deliverable, not an afterthought
- Spec acceptance criteria: "The scraper recovers gracefully from at least one simulated failure" — README should demonstrate this with real log output
- README should show the scraper surviving a Ctrl+C and resuming, as a concrete resilience demo
- Setup instructions should work with a single `pip install` + config file + run command

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — greenfield project. Phase 4 builds on whatever Phases 1-3 produce.

### Established Patterns
- Tech stack decided: Python 3.10+, Playwright, BeautifulSoup4, pandas, httpx
- Config-driven architecture: site-specific selectors in YAML/JSON config
- Structured logging with timestamps, URLs, error types (from Phase 1)
- CLI with argument overrides (from Phase 1)

### Integration Points
- Signal handlers hook into the main crawl loop (Phase 2's crawl engine)
- Checkpoint save/load integrates with the URL queue and visited set from the crawler
- Partial result persistence integrates with the output pipeline from Phase 3
- README documents capabilities built across all phases

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-resilience-and-documentation*
*Context gathered: 2026-03-13*
