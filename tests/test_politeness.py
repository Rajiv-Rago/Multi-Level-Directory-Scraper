"""Tests for politeness controller (robots.txt + delays)."""

import asyncio
import time

import httpx
import pytest
import respx
import structlog

from scraper.config import ScrapeConfig
from scraper.politeness import PolitenessController


def make_config(base_url="https://example.com", delay_min=1.0, delay_max=3.0):
    return ScrapeConfig.model_validate(
        {
            "site": {
                "name": "Test",
                "base_url": base_url,
                "request_delay": {"min": delay_min, "max": delay_max},
            },
            "levels": [
                {
                    "name": "items",
                    "depth": 0,
                    "link_selector": "a.item",
                    "fields": [{"name": "title", "selector": "h1"}],
                }
            ],
        }
    )


ROBOTS_TXT = """\
User-agent: *
Disallow: /private/
Disallow: /admin/

User-agent: multi-level-directory-scraper
Disallow: /private/
Disallow: /admin/
Crawl-delay: 5
"""

ROBOTS_TXT_SHORT_DELAY = """\
User-agent: *
Disallow: /private/

User-agent: multi-level-directory-scraper
Disallow: /private/
Crawl-delay: 0.5
"""


@pytest.fixture()
def logger():
    return structlog.get_logger()


class TestRobotsCompliance:
    @respx.mock
    def test_robots_allowed_url(self, logger):
        config = make_config()
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.is_allowed("https://example.com/public/page") is True

    @respx.mock
    def test_robots_disallowed_url(self, logger):
        config = make_config()
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.is_allowed("https://example.com/private/secret") is False

    @respx.mock
    def test_robots_crawl_delay_overrides_config(self, logger):
        config = make_config(delay_min=1.0)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.effective_delay_min == 5.0

    @respx.mock
    def test_robots_crawl_delay_shorter_than_config(self, logger):
        config = make_config(delay_min=1.0)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_SHORT_DELAY)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.effective_delay_min == 1.0

    @respx.mock
    def test_robots_fetch_failure_allows_all(self, logger):
        config = make_config()
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(404)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.is_allowed("https://example.com/private/secret") is True


class TestDelayBehavior:
    @respx.mock
    def test_delay_within_range(self, logger):
        config = make_config(delay_min=0.01, delay_max=0.02)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(404)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())

        delays = []
        for _ in range(20):
            start = time.monotonic()
            asyncio.run(controller.wait())
            elapsed = time.monotonic() - start
            delays.append(elapsed)

        for d in delays:
            assert d >= 0.01
            assert d < 0.05

    @respx.mock
    def test_delay_respects_robots_crawl_delay(self, logger):
        config = make_config(delay_min=1.0, delay_max=3.0)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT)
        )
        controller = PolitenessController(config, logger)
        asyncio.run(controller.initialize())
        assert controller.effective_delay_min == 5.0
