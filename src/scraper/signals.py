"""Signal handler for cooperative shutdown with checkpoint save on interruption."""

from __future__ import annotations

import logging
import signal
import sys
from typing import Callable

from scraper.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class SignalHandler:
    """Handles SIGINT/SIGTERM for cooperative shutdown with state persistence."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        get_state: Callable[[], dict],
        flush_results: Callable[[], None],
    ) -> None:
        self._checkpoint_manager = checkpoint_manager
        self._get_state = get_state
        self._flush_results = flush_results
        self.shutdown_requested: bool = False
        self.shutdown_count: int = 0

    def register(self) -> None:
        """Register signal handlers for SIGINT and SIGTERM."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame) -> None:
        self.shutdown_count += 1
        self.shutdown_requested = True

        if self.shutdown_count == 1:
            logger.info(
                "Received signal %s, finishing current page and saving state...",
                signal.Signals(signum).name,
            )
            self.save_state()
        else:
            logger.warning("Force shutdown -- saving emergency state...")
            self._emergency_save()
            sys.exit(1)

    def save_state(self) -> None:
        """Save current crawl state and flush partial results."""
        state = self._get_state()
        self._checkpoint_manager.save(state)
        self._flush_results()

        visited = len(state.get("visited_urls", set()))
        pending = len(state.get("pending_urls", []))
        records = state.get("records_extracted", 0)
        logger.info(
            "State saved: %d pages visited, %d pending, %d records",
            visited,
            pending,
            records,
        )

    def _emergency_save(self) -> None:
        """Best-effort save on second signal."""
        try:
            self.save_state()
        except Exception:
            logger.exception("Emergency save failed")

    def should_checkpoint(self, pages_since_last: int, interval: int = 50) -> bool:
        """Return True when it's time for a periodic checkpoint save."""
        return pages_since_last >= interval
