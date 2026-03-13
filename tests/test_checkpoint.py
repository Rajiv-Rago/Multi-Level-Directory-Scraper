"""Tests for checkpoint save/load, atomic writes, and resume logic."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scraper.checkpoint import CheckpointManager, config_hash


@pytest.fixture()
def manager(tmp_path):
    return CheckpointManager(output_dir=tmp_path, config_hash="abc123")


@pytest.fixture()
def sample_state():
    return {
        "visited_urls": {"https://example.com/a", "https://example.com/b", "https://example.com/c"},
        "pending_urls": [
            {"url": "https://example.com/d", "depth": 1, "ancestors": []},
        ],
        "records_extracted": 42,
    }


class TestSaveLoadRoundtrip:
    def test_roundtrip_preserves_state(self, manager, sample_state):
        manager.save(sample_state)
        loaded = manager.load()

        assert loaded is not None
        assert loaded["visited_urls"] == sample_state["visited_urls"]
        assert loaded["pending_urls"] == sample_state["pending_urls"]
        assert loaded["records_extracted"] == sample_state["records_extracted"]

    def test_visited_urls_roundtrip_through_set_list_set(self, manager, sample_state):
        manager.save(sample_state)
        loaded = manager.load()

        assert isinstance(loaded["visited_urls"], set)
        assert loaded["visited_urls"] == sample_state["visited_urls"]


class TestAtomicWrite:
    def test_checkpoint_file_is_valid_json(self, manager, sample_state):
        manager.save(sample_state)

        raw = manager.checkpoint_path.read_text()
        data = json.loads(raw)
        assert "visited_urls" in data
        assert "config_hash" in data

    def test_checkpoint_file_exists_after_save(self, manager, sample_state):
        assert not manager.exists
        manager.save(sample_state)
        assert manager.exists
        assert manager.checkpoint_path.is_file()


class TestConfigMismatch:
    def test_mismatch_returns_none_without_force(self, manager, sample_state):
        manager.save(sample_state)

        other_manager = CheckpointManager(
            output_dir=manager.checkpoint_path.parent,
            config_hash="different_hash",
        )
        result = other_manager.load(force=False)
        assert result is None

    def test_mismatch_returns_state_with_force(self, manager, sample_state):
        manager.save(sample_state)

        other_manager = CheckpointManager(
            output_dir=manager.checkpoint_path.parent,
            config_hash="different_hash",
        )
        result = other_manager.load(force=True)
        assert result is not None
        assert result["visited_urls"] == sample_state["visited_urls"]


class TestStaleCheckpoint:
    def test_stale_checkpoint_warns_but_loads(self, manager, sample_state, caplog):
        manager.save(sample_state)

        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        raw = json.loads(manager.checkpoint_path.read_text())
        raw["checkpoint_at"] = old_time
        manager.checkpoint_path.write_text(json.dumps(raw))

        import logging
        with caplog.at_level(logging.WARNING):
            result = manager.load()

        assert result is not None
        assert "stale" in caplog.text.lower() or "old" in caplog.text.lower()


class TestResumeSkipsVisited:
    def test_visited_urls_preserved_as_set(self, manager, sample_state):
        manager.save(sample_state)
        loaded = manager.load()

        assert "https://example.com/a" in loaded["visited_urls"]
        assert "https://example.com/b" in loaded["visited_urls"]
        assert "https://example.com/c" in loaded["visited_urls"]
        assert len(loaded["visited_urls"]) == 3


class TestCheckpointCleanup:
    def test_cleanup_deletes_file(self, manager, sample_state):
        manager.save(sample_state)
        assert manager.exists

        manager.cleanup()
        assert not manager.exists
        assert not manager.checkpoint_path.is_file()

    def test_cleanup_noop_when_no_file(self, manager):
        manager.cleanup()
        assert not manager.exists


class TestConfigHash:
    def test_same_config_same_hash(self):
        cfg = {"base_url": "https://example.com", "selectors": {"a": "b"}}
        assert config_hash(cfg) == config_hash(cfg)

    def test_different_config_different_hash(self):
        cfg1 = {"base_url": "https://example.com", "selectors": {"a": "b"}}
        cfg2 = {"base_url": "https://other.com", "selectors": {"a": "b"}}
        assert config_hash(cfg1) != config_hash(cfg2)

    def test_hash_is_16_hex_chars(self):
        cfg = {"base_url": "https://example.com", "selectors": {}}
        h = config_hash(cfg)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)
