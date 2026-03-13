"""Politeness controller: robots.txt compliance and request delays."""

from __future__ import annotations

import asyncio
import random
import re
from urllib.robotparser import RobotFileParser

import httpx

from scraper.config import ScrapeConfig

USER_AGENT = "multi-level-directory-scraper"


class PolitenessController:
    def __init__(self, config: ScrapeConfig, logger) -> None:
        self._config = config
        self._logger = logger
        self._robot_parser = RobotFileParser()
        self._allow_all = False
        self._crawl_delay: float = 0.0

    async def initialize(self) -> None:
        """Fetch and parse robots.txt from the target site's domain root."""
        from urllib.parse import urlparse

        parsed = urlparse(self._config.site.base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
            if response.status_code != 200:
                self._logger.warning("robots_txt_not_found", url=robots_url, status=response.status_code)
                self._allow_all = True
                return

            raw_text = response.text
            self._robot_parser.parse(raw_text.splitlines())
            self._crawl_delay = self._extract_crawl_delay(raw_text)
            self._logger.info(
                "robots_txt_loaded",
                url=robots_url,
                crawl_delay=self._crawl_delay,
            )
        except Exception as e:
            self._logger.warning("robots_txt_fetch_failed", url=robots_url, error=str(e))
            self._allow_all = True

    def _extract_crawl_delay(self, raw_text: str) -> float:
        """Extract Crawl-delay for our user-agent from raw robots.txt text."""
        current_agent = None
        for line in raw_text.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip().lower()
            elif line.lower().startswith("crawl-delay:") and current_agent == USER_AGENT:
                match = re.search(r"[\d.]+", line.split(":", 1)[1])
                if match:
                    return float(match.group())
        return 0.0

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by robots.txt rules."""
        if self._allow_all:
            return True
        allowed = self._robot_parser.can_fetch(USER_AGENT, url)
        if not allowed:
            self._logger.warning("url_disallowed_by_robots", url=url)
        return allowed

    async def wait(self) -> None:
        """Sleep for a randomized delay within the configured range."""
        delay = random.uniform(self.effective_delay_min, self._config.site.request_delay.max)
        self._logger.debug("request_delay", seconds=round(delay, 2))
        await asyncio.sleep(delay)

    @property
    def effective_delay_min(self) -> float:
        """Minimum delay considering both config and robots.txt Crawl-delay."""
        return max(self._config.site.request_delay.min, self._crawl_delay)
