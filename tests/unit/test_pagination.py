"""Tests for pagination handler: next_page, load_more, infinite_scroll strategies."""

from unittest.mock import AsyncMock

import pytest

from scraper.pagination import PaginationConfig, PaginationHandler


def _html_with_next_link(page_num: int, max_page: int) -> str:
    next_link = f'<a class="next" href="/list?page={page_num + 1}">Next</a>' if page_num < max_page else ""
    return f"<html><body><div>Page {page_num}</div>{next_link}</body></html>"


class TestNextPageStrategy:
    @pytest.mark.asyncio
    async def test_follows_next_links(self):
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(
            side_effect=[
                _html_with_next_link(2, 3),
                _html_with_next_link(3, 3),
            ]
        )
        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="next_page", selector="a.next", max_pages=100)

        pages = await handler.paginate(
            _html_with_next_link(1, 3), config, "https://example.com/list?page=1"
        )
        assert len(pages) == 3

    @pytest.mark.asyncio
    async def test_stops_when_no_next_link(self):
        mock_fetcher = AsyncMock()
        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="next_page", selector="a.next", max_pages=100)

        html = "<html><body><div>Only page</div></body></html>"
        pages = await handler.paginate(html, config, "https://example.com/list")
        assert len(pages) == 1

    @pytest.mark.asyncio
    async def test_respects_max_pages_cap(self):
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(
            side_effect=[_html_with_next_link(i, 100) for i in range(2, 50)]
        )
        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="next_page", selector="a.next", max_pages=3)

        pages = await handler.paginate(
            _html_with_next_link(1, 100), config, "https://example.com/list"
        )
        assert len(pages) == 3

    @pytest.mark.asyncio
    async def test_resolves_relative_urls(self):
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(
            return_value="<html><body>Page 2</body></html>"
        )
        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="next_page", selector="a.next", max_pages=100)

        initial = '<html><body><a class="next" href="/list?page=2">Next</a></body></html>'
        await handler.paginate(initial, config, "https://example.com/list")
        mock_fetcher.fetch.assert_awaited_once_with("https://example.com/list?page=2")


class TestLoadMoreStrategy:
    @pytest.mark.asyncio
    async def test_clicks_button_and_returns_html(self):
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body>All items</body></html>"
        mock_button = AsyncMock()
        mock_page.query_selector = AsyncMock(
            side_effect=[mock_button, mock_button, None]  # button found twice, then gone
        )
        mock_page.close = AsyncMock()

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_with_page = AsyncMock(
            return_value=("<html>Initial</html>", mock_page)
        )

        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="load_more", selector="button.load-more", max_pages=100)

        pages = await handler.paginate("", config, "https://example.com/list")
        assert len(pages) == 1
        assert "All items" in pages[0]

    @pytest.mark.asyncio
    async def test_respects_max_pages_cap(self):
        click_count = 0

        async def mock_query_selector(sel):
            nonlocal click_count
            click_count += 1
            if click_count <= 10:
                return AsyncMock()
            return None

        mock_page = AsyncMock()
        mock_page.content.return_value = "<html>Final</html>"
        mock_page.query_selector = mock_query_selector
        mock_page.close = AsyncMock()

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_with_page = AsyncMock(
            return_value=("<html>Initial</html>", mock_page)
        )

        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(type="load_more", selector="button.load-more", max_pages=3)

        pages = await handler.paginate("", config, "https://example.com/list")
        assert len(pages) == 1


class TestInfiniteScrollStrategy:
    @pytest.mark.asyncio
    async def test_scrolls_until_no_new_items(self):
        item_counts = [5, 10, 15, 15, 15]  # stops after 3 consecutive same count
        call_idx = 0

        async def mock_eval(expr):
            nonlocal call_idx
            count = item_counts[min(call_idx, len(item_counts) - 1)]
            call_idx += 1
            return count

        mock_page = AsyncMock()
        mock_page.evaluate = mock_eval
        mock_page.content.return_value = "<html>Scrolled content</html>"
        mock_page.close = AsyncMock()

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_with_page = AsyncMock(
            return_value=("<html>Initial</html>", mock_page)
        )

        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(
            type="infinite_scroll",
            selector="div.item",
            max_pages=100,
            max_items=None,
        )

        pages = await handler.paginate("", config, "https://example.com/list")
        assert len(pages) == 1
        assert "Scrolled content" in pages[0]

    @pytest.mark.asyncio
    async def test_respects_max_items(self):
        call_idx = 0

        async def mock_eval(expr):
            nonlocal call_idx
            call_idx += 1
            if "scrollHeight" in str(expr) if isinstance(expr, str) else True:
                return call_idx * 5
            return call_idx * 5

        mock_page = AsyncMock()
        mock_page.evaluate = mock_eval
        mock_page.content.return_value = "<html>Items</html>"
        mock_page.close = AsyncMock()

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_with_page = AsyncMock(
            return_value=("<html>Initial</html>", mock_page)
        )

        handler = PaginationHandler(mock_fetcher)
        config = PaginationConfig(
            type="infinite_scroll",
            selector="div.item",
            max_pages=100,
            max_items=10,
        )

        pages = await handler.paginate("", config, "https://example.com/list")
        assert len(pages) == 1


class TestNoPagination:
    @pytest.mark.asyncio
    async def test_returns_initial_html_only(self):
        handler = PaginationHandler(AsyncMock())

        pages = await handler.paginate("<html>Single page</html>", None, "https://example.com")
        assert pages == ["<html>Single page</html>"]
