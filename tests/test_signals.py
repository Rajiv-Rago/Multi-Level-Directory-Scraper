"""Tests for signal handling, cooperative shutdown, and partial result persistence."""

from __future__ import annotations

import signal
from unittest.mock import MagicMock

import pytest

from scraper.signals import SignalHandler


@pytest.fixture()
def mock_checkpoint_manager():
    manager = MagicMock()
    manager.save = MagicMock()
    return manager


@pytest.fixture()
def mock_state():
    return {
        "visited_urls": {"https://example.com/a", "https://example.com/b"},
        "pending_urls": [{"url": "https://example.com/c", "depth": 1, "ancestors": []}],
        "records_extracted": 10,
    }


@pytest.fixture()
def handler(mock_checkpoint_manager, mock_state):
    get_state = MagicMock(return_value=mock_state)
    flush_results = MagicMock()
    h = SignalHandler(
        checkpoint_manager=mock_checkpoint_manager,
        get_state=get_state,
        flush_results=flush_results,
    )
    return h


class TestSignalFlag:
    def test_shutdown_requested_initially_false(self, handler):
        assert handler.shutdown_requested is False

    def test_signal_sets_shutdown_flag(self, handler):
        handler._handle_signal(signal.SIGINT, None)
        assert handler.shutdown_requested is True

    def test_shutdown_count_increments(self, handler):
        assert handler.shutdown_count == 0
        handler._handle_signal(signal.SIGINT, None)
        assert handler.shutdown_count == 1


class TestDoubleSignal:
    def test_double_signal_increments_count(self, handler):
        handler._handle_signal(signal.SIGINT, None)
        assert handler.shutdown_count == 1

        with pytest.raises(SystemExit):
            handler._handle_signal(signal.SIGINT, None)

        assert handler.shutdown_count == 2


class TestCheckpointOnSignal:
    def test_save_state_calls_checkpoint_save(self, handler, mock_checkpoint_manager, mock_state):
        handler.save_state()

        mock_checkpoint_manager.save.assert_called_once_with(mock_state)

    def test_save_state_calls_flush_results(self, handler):
        handler.save_state()

        handler._flush_results.assert_called_once()


class TestPartialResults:
    def test_first_signal_triggers_save(self, handler, mock_checkpoint_manager, mock_state):
        handler._handle_signal(signal.SIGINT, None)

        mock_checkpoint_manager.save.assert_called_once_with(mock_state)

    def test_flush_called_on_first_signal(self, handler):
        handler._handle_signal(signal.SIGINT, None)

        handler._flush_results.assert_called_once()


class TestCooperativeShutdown:
    def test_crawl_loop_checks_flag(self, handler):
        pages_processed = 0
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]

        for url in urls:
            if handler.shutdown_requested:
                break
            pages_processed += 1
            if pages_processed == 2:
                handler._handle_signal(signal.SIGINT, None)

        assert pages_processed == 2
        assert handler.shutdown_requested is True


class TestPeriodicCheckpoint:
    def test_should_checkpoint_at_interval(self, handler):
        assert handler.should_checkpoint(49, interval=50) is False
        assert handler.should_checkpoint(50, interval=50) is True
        assert handler.should_checkpoint(100, interval=50) is True

    def test_should_checkpoint_default_interval(self, handler):
        assert handler.should_checkpoint(49) is False
        assert handler.should_checkpoint(50) is True
