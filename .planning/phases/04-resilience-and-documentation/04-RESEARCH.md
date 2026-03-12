# Phase 4: Resilience and Documentation - Research

**Researched:** 2026-03-13
**Phase Goal:** The scraper survives interruptions without losing work, and the project is documented as a portfolio piece
**Requirements:** RES-05, RES-07, RES-08, DOC-01

## 1. Signal Handling in Python

### SIGINT and SIGTERM Registration

Python's `signal` module allows registering handlers for SIGINT (Ctrl+C) and SIGTERM:

```python
import signal

shutdown_requested = False
shutdown_count = 0

def handle_signal(signum, frame):
    global shutdown_requested, shutdown_count
    shutdown_count += 1
    shutdown_requested = True
    if shutdown_count >= 2:
        # Second signal = immediate exit after saving what we can
        emergency_save()
        sys.exit(1)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
```

### Key Constraints

- Signal handlers run in the main thread only. If using asyncio or threading, the handler must communicate via a flag or event.
- The handler should be lightweight — set a flag, don't do heavy I/O in the handler itself.
- For asyncio event loops, use `loop.add_signal_handler()` instead of `signal.signal()`.
- On Windows, only SIGINT (via Ctrl+C) is reliably supported; SIGTERM may not work. Not a concern for this portfolio project targeting Linux/macOS.

### Pattern: Cooperative Shutdown

The recommended pattern is **cooperative shutdown** — the signal handler sets a flag, and the main crawl loop checks it between pages:

```python
for url in pending_urls:
    if shutdown_requested:
        save_checkpoint()
        save_partial_results()
        break
    process_page(url)
```

This avoids partial state corruption from interrupting mid-operation.

### Double-Signal Pattern

- First signal: set `shutdown_requested = True`, let current page finish, save state gracefully.
- Second signal: emergency save — write whatever state is available immediately, then exit.

This matches user expectations (Ctrl+C once = graceful, Ctrl+C twice = force quit).

## 2. Checkpoint State Design

### What to Persist

The checkpoint must capture enough state to resume the crawl without re-visiting pages:

| Field | Purpose |
|-------|---------|
| `visited_urls` | Set of URLs already fetched — prevents re-scraping |
| `pending_urls` | Queue of URLs remaining to process (with their level/context) |
| `current_level` | Which navigation level the crawler is on |
| `records_extracted` | Count of records extracted so far |
| `config_hash` | Hash of the config used — detect config changes on resume |
| `started_at` | Timestamp of the original run start |
| `checkpoint_at` | Timestamp of this checkpoint |
| `version` | Checkpoint format version for forward compatibility |

### File Format: JSON

JSON is the right choice per context decisions:
- Human-readable and debuggable
- No external dependencies
- Python's `json` module handles sets (serialize as lists)
- Checkpoint files are small (URL lists + metadata)

### Atomic Writes

Critical to prevent corrupt checkpoints if the process crashes during write:

```python
import tempfile
import os

def save_checkpoint(state, checkpoint_path):
    dir_name = os.path.dirname(checkpoint_path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, checkpoint_path)  # atomic on POSIX
    except:
        os.unlink(tmp_path)
        raise
```

`os.replace()` is atomic on POSIX systems — the checkpoint file is either the old version or the new version, never corrupt.

### Checkpoint Location

Co-located with output files in the output directory (per context decision). Naming: `.checkpoint.json` (dotfile to stay out of the way of output files).

## 3. Resume Logic

### Resume Flow

```
On startup:
  1. Check for checkpoint file in output directory
  2. If found:
     a. Validate config_hash matches current config
     b. If mismatch: warn, require --force to proceed
     c. If stale (>24h): warn but allow resume
     d. Load visited_urls, pending_urls, counters
     e. Log "Resuming from checkpoint: N pages visited, M remaining"
  3. If --resume flag but no checkpoint: error "No checkpoint found"
  4. If checkpoint found but no --resume flag: prompt user
  5. On successful completion: delete checkpoint file
```

### Config Mismatch Detection

Hash the config file content (or key fields: base_url, selectors) with hashlib:

```python
import hashlib

def config_hash(config):
    key_fields = json.dumps({
        'base_url': config['base_url'],
        'selectors': config['selectors']
    }, sort_keys=True)
    return hashlib.sha256(key_fields.encode()).hexdigest()[:16]
```

This catches cases where the user changed the config between runs — resuming with different selectors would produce inconsistent data.

## 4. Periodic Checkpointing

### Strategy

- Save after every N pages (default 50, configurable).
- Save after completing each navigation level (natural breakpoint).
- Use atomic writes to avoid corruption.

### Integration with Crawl Loop

```python
pages_since_checkpoint = 0

for url in pending_urls:
    if shutdown_requested:
        break

    process_page(url)
    pages_since_checkpoint += 1

    if pages_since_checkpoint >= checkpoint_interval:
        save_checkpoint(state)
        pages_since_checkpoint = 0
```

## 5. Partial Result Persistence (RES-05)

### Approach: Incremental Writes

Rather than buffering all records in memory and writing at the end, flush records to disk incrementally:

- **CSV**: Open in append mode. Write header once, then append rows as extracted.
- **JSON**: Trickier — can't append to a JSON array. Options:
  1. Write NDJSON (one JSON object per line) during crawl, convert to final nested JSON on completion.
  2. Keep records in memory, write to JSON on checkpoint/completion.

  Option 1 (NDJSON intermediate) is safer — records survive even if the process is killed without graceful shutdown.

### Marking Partial Output

Per context decision, mark output as partial:
- Include a metadata field in the output filename or a companion `.meta.json` file
- On resume: continue appending to the partial file
- On completion: rename to remove "partial" indicator, or update the metadata file

### Simpler Alternative

Use a `.meta.json` file alongside outputs:

```json
{
  "status": "partial",
  "records_written": 142,
  "started_at": "2026-03-13T10:00:00Z",
  "last_updated": "2026-03-13T10:05:00Z"
}
```

On completion, update to `"status": "complete"`. This avoids renaming files and keeps the output filenames stable.

## 6. README Structure for Portfolio

### Key Sections (from context + spec section 6)

1. **Title + Badges** — Python version, license, build status (if CI added later)
2. **Problem Statement** — What the tool does, why the target site is non-trivial (JS rendering, multi-level navigation, pagination)
3. **Key Features** — Bullet list of capabilities
4. **Quick Start** — 3-step setup: clone, install, run
5. **Architecture / Approach** — Key design decisions (why Playwright, config-driven selectors, multi-level traversal strategy)
6. **Data Quality** — Validation stats, field completeness metrics
7. **Resilience** — How the scraper handles failures, with real log output snippets showing:
   - HTTP retry in action
   - Timeout recovery
   - Checkpoint save on Ctrl+C
   - Resume from checkpoint
8. **Sample Output** — Truncated CSV and JSON showing actual extracted data
9. **Configuration** — Config file format with annotated example
10. **Setup Instructions** — Detailed install steps (under 5 minutes)

### Tone

Per context: "technical but accessible — written for hiring managers and senior engineers reviewing a portfolio." This means:
- No jargon without explanation
- Lead with results (what it does) before implementation details
- Show, don't tell — use actual output snippets, not claims

### Log Output Snippets

The README should include real (or realistic) log output showing resilience in action:

```
[2026-03-13 10:05:23] INFO  Scraping page 47/312 - https://example.com/region/tech
[2026-03-13 10:05:25] WARN  HTTP 429 on https://example.com/listing/42 - backing off 5s (attempt 1/3)
[2026-03-13 10:05:30] INFO  Retry successful - https://example.com/listing/42
[2026-03-13 10:05:45] INFO  ^C received - saving checkpoint...
[2026-03-13 10:05:45] INFO  Checkpoint saved: 47 pages visited, 265 remaining
[2026-03-13 10:05:46] INFO  Partial results saved: 142 records to output/data.csv
```

## 7. Testing Resilience

### Signal Handling Tests

- Spawn scraper as subprocess, send SIGINT after N seconds, verify checkpoint file exists and partial output is written.
- Send SIGINT twice rapidly, verify emergency save still writes state.

### Resume Tests

- Create a checkpoint file manually, run with --resume, verify it skips already-visited URLs.
- Modify config, run with --resume, verify warning about config mismatch.

### Integration Test

- Run against a mock server, interrupt mid-crawl, resume, verify final output contains all records with no duplicates.

## 8. Validation Architecture

### Test Strategy for Phase 4

| Requirement | Test Type | What to Verify |
|-------------|-----------|----------------|
| RES-05 | Integration | Send SIGINT to subprocess, verify partial output file exists with records |
| RES-07 | Unit + Integration | Unit: checkpoint serialization/deserialization. Integration: periodic checkpoint during crawl |
| RES-08 | Integration | Create checkpoint, restart with --resume, verify no re-scraping of visited URLs |
| DOC-01 | Manual + Automated | README exists, contains required sections, setup instructions work |

### Mock Server Approach

Use a simple HTTP server (e.g., `http.server` or pytest fixture) that serves fake directory pages. This allows:
- Deterministic test data
- Control over timing (slow responses to test interruption)
- No dependency on external sites during testing

## RESEARCH COMPLETE

Research covers all four Phase 4 requirements (RES-05, RES-07, RES-08, DOC-01) with concrete implementation patterns for signal handling, checkpoint persistence, resume logic, partial result saving, and portfolio README structure.
