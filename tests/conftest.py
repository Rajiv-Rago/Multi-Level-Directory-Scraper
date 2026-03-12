"""Shared test fixtures."""

from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def valid_config_dict():
    return {
        "site": {
            "name": "Test Directory",
            "base_url": "https://example.com",
            "output_dir": "./output",
            "request_delay": {"min": 1.0, "max": 3.0},
            "max_pages": 100,
            "log_level": "info",
        },
        "levels": [
            {
                "name": "regions",
                "depth": 0,
                "link_selector": "a.region-link",
                "fields": [
                    {"name": "region_name", "selector": "h2.title"},
                    {"name": "region_url", "selector": "a.region-link", "attribute": "href"},
                ],
            },
            {
                "name": "listings",
                "depth": 1,
                "link_selector": "a.listing-link",
                "fields": [
                    {"name": "listing_name", "selector": "h3.name"},
                    {"name": "address", "selector": "span.address"},
                ],
            },
        ],
    }


@pytest.fixture()
def minimal_config_dict():
    return {
        "site": {
            "name": "Minimal",
            "base_url": "https://example.com",
        },
        "levels": [
            {
                "name": "items",
                "depth": 0,
                "link_selector": "a.item",
                "fields": [{"name": "title", "selector": "h1"}],
            },
        ],
    }


@pytest.fixture()
def write_config(tmp_path):
    def _write(config_dict: dict) -> Path:
        path = tmp_path / "config.yaml"
        path.write_text(yaml.dump(config_dict))
        return path

    return _write
