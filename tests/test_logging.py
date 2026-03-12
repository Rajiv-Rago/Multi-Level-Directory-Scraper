"""Tests for structured logging configuration."""

import json

import structlog

from scraper.logging import setup_logging


class TestLogging:
    def test_json_log_contains_required_fields(self, tmp_path):
        log_file = tmp_path / "test.log"
        setup_logging("info", log_file)
        logger = structlog.get_logger()
        logger.info("test_event", url="https://example.com")

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert "timestamp" in entry
        assert "level" in entry
        assert "event" in entry
        assert entry["event"] == "test_event"

    def test_log_level_filtering(self, tmp_path):
        log_file = tmp_path / "test.log"
        setup_logging("warning", log_file)
        logger = structlog.get_logger()
        logger.info("should_not_appear")
        logger.warning("should_appear")

        content = log_file.read_text()
        assert "should_not_appear" not in content
        assert "should_appear" in content

    def test_log_file_created(self, tmp_path):
        log_file = tmp_path / "logs" / "test.log"
        log_file.parent.mkdir(parents=True)
        setup_logging("info", log_file)
        logger = structlog.get_logger()
        logger.info("init")

        assert log_file.exists()
        assert log_file.stat().st_size > 0

    def test_no_log_file_when_none(self):
        setup_logging("info", None)
        logger = structlog.get_logger()
        logger.info("no_file_event")
