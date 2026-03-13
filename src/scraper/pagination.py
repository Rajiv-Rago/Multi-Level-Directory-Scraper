"""Pagination handler with next_page, load_more, and infinite_scroll strategies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from scraper.extractor import get_base_url

logger = structlog.get_logger()


@dataclass
class PaginationConfig:
    type: Literal["next_page", "load_more", "infinite_scroll"]
    selector: str
    max_pages: int = 100
    max_items: int | None = None
    content_selector: str | None = None


class PaginationHandler:
    """Handles paginated listings using multiple strategies."""

    def __init__(self, fetcher) -> None:
        self._fetcher = fetcher

    async def paginate(
        self,
        initial_html: str,
        pagination_config: PaginationConfig | None,
        base_url: str,
    ) -> list[str]:
        if pagination_config is None:
            return [initial_html]

        strategy = pagination_config.type
        if strategy == "next_page":
            return await self._next_page(initial_html, pagination_config, base_url)
        elif strategy == "load_more":
            return await self._load_more(pagination_config, base_url)
        elif strategy == "infinite_scroll":
            return await self._infinite_scroll(pagination_config, base_url)

        return [initial_html]

    async def _next_page(
        self, initial_html: str, config: PaginationConfig, page_url: str
    ) -> list[str]:
        pages = [initial_html]
        current_html = initial_html

        while len(pages) < config.max_pages:
            soup = BeautifulSoup(current_html, "lxml")
            next_el = soup.select_one(config.selector)
            if next_el is None or not next_el.get("href"):
                break

            base_url = get_base_url(current_html, page_url)
            next_url = urljoin(base_url, next_el["href"])
            current_html = await self._fetcher.fetch(next_url)
            if current_html is None:
                break
            pages.append(current_html)

        logger.info("pagination_complete", strategy="next_page", pages=len(pages))
        return pages

    async def _load_more(
        self, config: PaginationConfig, base_url: str
    ) -> list[str]:
        _, page = await self._fetcher.fetch_with_page(base_url)
        try:
            clicks = 0
            while clicks < config.max_pages:
                button = await page.query_selector(config.selector)
                if button is None:
                    break
                await button.click()
                await asyncio.sleep(0.5)
                clicks += 1

            html = await page.content()
            logger.info("pagination_complete", strategy="load_more", clicks=clicks)
            return [html]
        finally:
            await page.close()

    async def _infinite_scroll(
        self, config: PaginationConfig, base_url: str
    ) -> list[str]:
        _, page = await self._fetcher.fetch_with_page(base_url)
        try:
            prev_count = 0
            stale_scrolls = 0
            scroll_count = 0

            while scroll_count < config.max_pages:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)
                scroll_count += 1

                current_count = await page.evaluate(
                    f'document.querySelectorAll("{config.selector}").length'
                )

                if current_count == prev_count:
                    stale_scrolls += 1
                    if stale_scrolls >= 3:
                        break
                else:
                    stale_scrolls = 0

                if config.max_items and current_count >= config.max_items:
                    break

                prev_count = current_count

            html = await page.content()
            logger.info(
                "pagination_complete",
                strategy="infinite_scroll",
                scrolls=scroll_count,
                items=prev_count,
            )
            return [html]
        finally:
            await page.close()
