"""Tests for retry logic with exponential backoff for 429 and fixed retry for 5xx."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from scraper.fetcher import RateLimitError, ServerError
from scraper.retry import with_retry


def _make_response(status_code: int) -> httpx.Response:
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    return mock


class TestRateLimitRetry:
    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_then_succeeds(self):
        mock_fetch = AsyncMock(
            side_effect=[
                RateLimitError(_make_response(429)),
                RateLimitError(_make_response(429)),
                "<html>Success</html>",
            ]
        )
        wrapped = with_retry(mock_fetch)
        result = await wrapped("https://example.com")
        assert result == "<html>Success</html>"
        assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_attempts_on_persistent_rate_limit(self):
        mock_fetch = AsyncMock(
            side_effect=RateLimitError(_make_response(429))
        )
        wrapped = with_retry(mock_fetch)
        with pytest.raises(RateLimitError):
            await wrapped("https://example.com")
        assert mock_fetch.call_count == 3


class TestServerErrorRetry:
    @pytest.mark.asyncio
    async def test_retries_once_on_server_error(self):
        mock_fetch = AsyncMock(
            side_effect=[
                ServerError(_make_response(500)),
                "<html>Recovered</html>",
            ]
        )
        wrapped = with_retry(mock_fetch)
        result = await wrapped("https://example.com")
        assert result == "<html>Recovered</html>"
        assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_two_server_errors(self):
        mock_fetch = AsyncMock(
            side_effect=ServerError(_make_response(500))
        )
        wrapped = with_retry(mock_fetch)
        with pytest.raises(ServerError):
            await wrapped("https://example.com")
        assert mock_fetch.call_count == 2


class TestNoRetryOn404:
    @pytest.mark.asyncio
    async def test_none_returned_without_retry(self):
        mock_fetch = AsyncMock(return_value=None)
        wrapped = with_retry(mock_fetch)
        result = await wrapped("https://example.com")
        assert result is None
        assert mock_fetch.call_count == 1


class TestCombinedBehavior:
    @pytest.mark.asyncio
    async def test_other_exceptions_propagate_immediately(self):
        mock_fetch = AsyncMock(side_effect=ValueError("unexpected"))
        wrapped = with_retry(mock_fetch)
        with pytest.raises(ValueError, match="unexpected"):
            await wrapped("https://example.com")
        assert mock_fetch.call_count == 1
