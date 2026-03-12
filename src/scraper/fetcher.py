"""Dual-mode fetcher: Playwright for JS-rendered pages, httpx for static pages."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx
import structlog
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

logger = structlog.get_logger()


class RateLimitError(Exception):
    """Raised on HTTP 429 responses."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"Rate limited: {response.status_code}")


class ServerError(Exception):
    """Raised on HTTP 5xx responses."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"Server error: {response.status_code}")


@runtime_checkable
class Fetcher(Protocol):
    async def fetch(self, url: str, *, wait_selector: str | None = None, timeout: float = 15.0) -> str | None: ...
    async def close(self) -> None: ...


class PlaywrightFetcher:
    """Fetcher using Playwright for JS-rendered pages."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._context = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context()

    async def fetch(self, url: str, *, wait_selector: str | None = None, timeout: float = 15.0) -> str | None:
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            timeout_ms = int(timeout * 1000)
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout_ms)
            else:
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return await page.content()
        except PlaywrightTimeout:
            logger.warning("playwright_timeout", url=url, timeout=timeout)
            return await page.content()
        except Exception:
            logger.exception("playwright_fetch_error", url=url)
            return None
        finally:
            await page.close()

    async def fetch_with_page(self, url: str, *, wait_selector: str | None = None, timeout: float = 15.0):
        """Fetch a page and return (html, page) tuple. Caller must close page."""
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            timeout_ms = int(timeout * 1000)
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout_ms)
            else:
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except PlaywrightTimeout:
            logger.warning("playwright_timeout", url=url, timeout=timeout)
        except Exception:
            logger.exception("playwright_fetch_error", url=url)
        html = await page.content()
        return html, page

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


class HttpxFetcher:
    """Fetcher using httpx for static pages."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0, read=30.0),
            follow_redirects=True,
        )

    async def fetch(self, url: str, **kwargs) -> str | None:
        try:
            response = await self._client.get(url)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            logger.warning("httpx_connection_error", url=url)
            return None

        if response.status_code == 429:
            raise RateLimitError(response)
        if response.status_code >= 500:
            raise ServerError(response)
        if response.status_code == 404:
            logger.info("httpx_not_found", url=url)
            return None

        return response.text

    async def close(self) -> None:
        await self._client.aclose()
