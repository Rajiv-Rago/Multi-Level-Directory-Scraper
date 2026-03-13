"""Tests for config loading and validation."""

import pytest

from scraper.config import apply_overrides, load_config


class TestConfigLoading:
    def test_valid_config_loads(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        config = load_config(path)
        assert config.site.name == "Test Directory"
        assert config.site.base_url == "https://example.com"
        assert len(config.levels) == 2
        assert config.levels[0].name == "regions"
        assert config.levels[1].fields[0].name == "listing_name"

    def test_minimal_config_defaults(self, minimal_config_dict, write_config):
        path = write_config(minimal_config_dict)
        config = load_config(path)
        assert config.site.output_dir == "./output"
        assert config.site.request_delay.min == 1.0
        assert config.site.request_delay.max == 3.0
        assert config.site.max_pages is None
        assert config.site.log_level == "info"
        assert config.levels[0].fields[0].attribute == "text"

    def test_missing_required_field_error(self, valid_config_dict, write_config):
        del valid_config_dict["site"]["base_url"]
        path = write_config(valid_config_dict)
        with pytest.raises(SystemExit):
            load_config(path)

    def test_invalid_delay_range(self, valid_config_dict, write_config):
        valid_config_dict["site"]["request_delay"] = {"min": 5.0, "max": 2.0}
        path = write_config(valid_config_dict)
        with pytest.raises(SystemExit):
            load_config(path)

    def test_duplicate_level_names(self, valid_config_dict, write_config):
        valid_config_dict["levels"][1]["name"] = "regions"
        path = write_config(valid_config_dict)
        with pytest.raises(SystemExit):
            load_config(path)

    def test_config_is_immutable(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        config = load_config(path)
        with pytest.raises(Exception):
            config.site.name = "changed"

    def test_load_nonexistent_file(self):
        from pathlib import Path

        with pytest.raises(SystemExit):
            load_config(Path("nonexistent.yaml"))


class TestApplyOverrides:
    def test_apply_overrides(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        config = load_config(path)
        updated = apply_overrides(
            config,
            {"output_dir": "/tmp/out", "delay_min": 2.0, "delay_max": 5.0, "max_pages": 50, "log_level": "debug"},
        )
        assert updated.site.output_dir == "/tmp/out"
        assert updated.site.request_delay.min == 2.0
        assert updated.site.request_delay.max == 5.0
        assert updated.site.max_pages == 50
        assert updated.site.log_level == "debug"

    def test_apply_overrides_none_values_ignored(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        config = load_config(path)
        updated = apply_overrides(config, {"output_dir": None, "max_pages": None})
        assert updated.site.output_dir == config.site.output_dir
        assert updated.site.max_pages == config.site.max_pages
