"""Checkpoint manager for saving and resuming crawl state with atomic writes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_VERSION = 1
STALE_THRESHOLD_HOURS = 24


def config_hash(config: dict) -> str:
    """Hash config fields to detect config changes between runs."""
    serialized = json.dumps(config, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class CheckpointManager:
    """Manages checkpoint save/load with atomic writes for crash resilience."""

    def __init__(self, output_dir: Path, config_hash: str) -> None:
        self._output_dir = Path(output_dir)
        self._config_hash = config_hash

    @property
    def checkpoint_path(self) -> Path:
        return self._output_dir / ".checkpoint.json"

    @property
    def exists(self) -> bool:
        return self.checkpoint_path.is_file()

    def save(self, state: dict) -> None:
        """Atomically save crawl state to checkpoint file."""
        visited = state.get("visited_urls", set())
        data = {
            "version": CHECKPOINT_VERSION,
            "config_hash": self._config_hash,
            "started_at": state.get("started_at", datetime.now(UTC).isoformat()),
            "checkpoint_at": datetime.now(UTC).isoformat(),
            "visited_urls": sorted(visited),
            "pending_urls": state.get("pending_urls", []),
            "records_extracted": state.get("records_extracted", 0),
        }

        self._output_dir.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=self._output_dir, suffix=".tmp", prefix=".checkpoint_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.checkpoint_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        logger.info(
            "Checkpoint saved: %d pages visited, %d pending",
            len(visited),
            len(data["pending_urls"]),
        )

    def load(self, force: bool = False) -> dict | None:
        """Load checkpoint, verifying config hash. Returns None if no checkpoint or mismatch."""
        if not self.exists:
            return None

        with open(self.checkpoint_path) as f:
            data = json.load(f)

        if data.get("config_hash") != self._config_hash:
            if not force:
                logger.warning(
                    "Checkpoint config mismatch (expected %s, got %s). "
                    "Use --force to resume with different config.",
                    self._config_hash,
                    data.get("config_hash"),
                )
                return None
            logger.warning(
                "Forcing resume with mismatched config (expected %s, got %s)",
                self._config_hash,
                data.get("config_hash"),
            )

        checkpoint_at = data.get("checkpoint_at")
        if checkpoint_at:
            checkpoint_time = datetime.fromisoformat(checkpoint_at)
            if checkpoint_time.tzinfo is None:
                checkpoint_time = checkpoint_time.replace(tzinfo=UTC)
            age = datetime.now(UTC) - checkpoint_time
            if age > timedelta(hours=STALE_THRESHOLD_HOURS):
                logger.warning(
                    "Stale checkpoint (%.1f hours old). Proceeding with resume.",
                    age.total_seconds() / 3600,
                )

        data["visited_urls"] = set(data.get("visited_urls", []))
        return data

    def cleanup(self) -> None:
        """Delete checkpoint file after successful completion."""
        if self.exists:
            self.checkpoint_path.unlink()
            logger.info("Checkpoint file cleaned up")

    def should_checkpoint(self, pages_since_last: int, interval: int = 50) -> bool:
        """Return True when it's time for a periodic checkpoint save."""
        return pages_since_last >= interval
