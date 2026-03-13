"""Tests for dual-mode fetcher (Playwright + httpx)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from scraper.fetcher import (
    HttpxFetcher,
    PlaywrightFetcher,
    RateLimitError,
    ServerError,
)


class TestPlaywrightFetcher:
    @pytest.mark.asyncio
    async def test_returns_html_content(self):
        fetcher = PlaywrightFetcher()
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body>Hello</body></html>"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        fetcher._context = mock_context

        result = await fetcher.fetch("https://example.com")
        assert result == "<html><body>Hello</body></html>"
        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_waits_for_selector_when_provided(self):
        fetcher = PlaywrightFetcher()
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html></html>"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        fetcher._context = mock_context

        await fetcher.fetch("https://example.com", wait_selector="div.results")
        mock_page.wait_for_selector.assert_awaited_once_with("div.results", timeout=15000)

    @pytest.mark.asyncio
    async def test_falls_back_to_networkidle_without_selector(self):
        fetcher = PlaywrightFetcher()
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html></html>"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        fetcher._context = mock_context

        await fetcher.fetch("https://example.com")
        mock_page.wait_for_load_state.assert_awaited_once_with("networkidle", timeout=15000)

    @pytest.mark.asyncio
    async def test_logs_warning_and_returns_partial_on_timeout(self):
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        fetcher = PlaywrightFetcher()
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body>Partial</body></html>"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        fetcher._context = mock_context

        result = await fetcher.fetch("https://example.com")
        assert result == "<html><body>Partial</body></html>"
        mock_page.close.assert_awaited_once()


class TestHttpxFetcher:
    @pytest.mark.asyncio
    async def test_returns_response_text(self):
        fetcher = HttpxFetcher()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "<html>Success</html>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        fetcher._client = mock_client

        result = await fetcher.fetch("https://example.com")
        assert result == "<html>Success</html>"

    @pytest.mark.asyncio
    async def test_raises_rate_limit_error_on_429(self):
        fetcher = HttpxFetcher()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        fetcher._client = mock_client

        with pytest.raises(RateLimitError):
            await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_raises_server_error_on_5xx(self):
        fetcher = HttpxFetcher()
        for status_code in (500, 502, 503):
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = status_code

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            fetcher._client = mock_client

            with pytest.raises(ServerError):
                await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        fetcher = HttpxFetcher()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        fetcher._client = mock_client

        result = await fetcher.fetch("https://example.com/missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_connection_timeout(self):
        fetcher = HttpxFetcher()
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectTimeout("timeout")
        fetcher._client = mock_client

        result = await fetcher.fetch("https://example.com")
        assert result is None
