"""Integration tests for crawl orchestrator with local test server."""

import asyncio

import pytest
import pytest_asyncio
from aiohttp import web

from scraper.extractor import Extractor
from scraper.frontier import URLFrontier
from scraper.orchestrator import CrawlConfig, CrawlOrchestrator, LevelConfig
from scraper.pagination import PaginationConfig, PaginationHandler

DIRECTORY_HTML = """
<html><body>
  <h1>Directory</h1>
  <a class="region-link" href="/directory/region-a">Region A</a>
  <a class="region-link" href="/directory/region-b">Region B</a>
</body></html>
"""

REGION_A_PAGE1 = """
<html><body>
  <h2 class="region-title">Region A</h2>
  <a class="listing-link" href="/detail/1">Item 1</a>
  <a class="listing-link" href="/detail/2">Item 2</a>
  <a class="next" href="/directory/region-a?page=2">Next</a>
</body></html>
"""

REGION_A_PAGE2 = """
<html><body>
  <h2 class="region-title">Region A</h2>
  <a class="listing-link" href="/detail/3">Item 3</a>
</body></html>
"""

REGION_B_HTML = """
<html><body>
  <h2 class="region-title">Region B</h2>
  <a class="listing-link" href="/detail/4">Item 4</a>
</body></html>
"""

DETAIL_TEMPLATE = """
<html><body>
  <h1 class="name">{name}</h1>
  <span class="address">{address}</span>
  <span class="phone">{phone}</span>
</body></html>
"""

DETAILS = {
    "1": ("Acme Corp", "123 Main St", "555-0001"),
    "2": ("Beta Inc", "456 Oak Ave", "555-0002"),
    "3": ("Gamma LLC", "789 Pine Rd", "555-0003"),
    "4": ("Delta Co", "321 Elm Blvd", "555-0004"),
}


def create_test_app():
    app = web.Application()

    async def handle_directory(request):
        return web.Response(text=DIRECTORY_HTML, content_type="text/html")

    async def handle_region_a(request):
        page = request.query.get("page", "1")
        html = REGION_A_PAGE2 if page == "2" else REGION_A_PAGE1
        return web.Response(text=html, content_type="text/html")

    async def handle_region_b(request):
        return web.Response(text=REGION_B_HTML, content_type="text/html")

    async def handle_detail(request):
        detail_id = request.match_info["id"]
        if detail_id in DETAILS:
            name, address, phone = DETAILS[detail_id]
            html = DETAIL_TEMPLATE.format(name=name, address=address, phone=phone)
            return web.Response(text=html, content_type="text/html")
        return web.Response(status=404)

    app.router.add_get("/directory", handle_directory)
    app.router.add_get("/directory/region-a", handle_region_a)
    app.router.add_get("/directory/region-b", handle_region_b)
    app.router.add_get("/detail/{id}", handle_detail)

    return app


class MockHttpFetcher:
    """Simple fetcher that uses httpx against a local test server."""

    def __init__(self, base_url: str):
        import httpx
        self._client = httpx.AsyncClient(base_url=base_url)

    async def fetch(self, url: str, **kwargs) -> str | None:
        try:
            response = await self._client.get(url)
            if response.status_code == 404:
                return None
            return response.text
        except Exception:
            return None

    async def close(self):
        await self._client.aclose()


@pytest_asyncio.fixture()
async def test_server():
    app = create_test_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    await runner.cleanup()


def _make_crawl_config(base_url: str) -> CrawlConfig:
    return CrawlConfig(
        base_url=f"{base_url}/directory",
        levels=[
            LevelConfig(
                depth=0,
                name="homepage",
                link_selector="a.region-link",
            ),
            LevelConfig(
                depth=1,
                name="region",
                link_selector="a.listing-link",
                context_selector="h2.region-title",
                pagination=PaginationConfig(type="next_page", selector="a.next", max_pages=10),
            ),
            LevelConfig(
                depth=2,
                name="detail",
                is_detail=True,
                fields=[
                    {"name": "name", "selectors": ["h1.name"]},
                    {"name": "address", "selectors": ["span.address"]},
                    {"name": "phone", "selectors": ["span.phone"]},
                ],
            ),
        ],
    )


class TestFullTraversal:
    @pytest.mark.asyncio
    async def test_extracts_all_records(self, test_server):
        config = _make_crawl_config(test_server)
        fetcher = MockHttpFetcher(test_server)
        extractor = Extractor()
        frontier = URLFrontier()
        pagination = PaginationHandler(fetcher)

        orchestrator = CrawlOrchestrator(
            config=config,
            fetcher=fetcher,
            extractor=extractor,
            frontier=frontier,
            pagination_handler=pagination,
        )

        records = await orchestrator.crawl()
        await fetcher.close()

        assert len(records) == 4
        names = {r["name"] for r in records}
        assert names == {"Acme Corp", "Beta Inc", "Gamma LLC", "Delta Co"}

    @pytest.mark.asyncio
    async def test_ancestor_context_propagated(self, test_server):
        config = _make_crawl_config(test_server)
        fetcher = MockHttpFetcher(test_server)
        extractor = Extractor()
        frontier = URLFrontier()
        pagination = PaginationHandler(fetcher)

        orchestrator = CrawlOrchestrator(
            config=config,
            fetcher=fetcher,
            extractor=extractor,
            frontier=frontier,
            pagination_handler=pagination,
        )

        records = await orchestrator.crawl()
        await fetcher.close()

        for record in records:
            assert "_ancestors" in record
            assert len(record["_ancestors"]) == 2  # homepage + region
            assert record["_ancestors"][1]["level"] == "region"
            assert record["_ancestors"][1]["label"] in ("Region A", "Region B")

    @pytest.mark.asyncio
    async def test_pagination_followed(self, test_server):
        config = _make_crawl_config(test_server)
        fetcher = MockHttpFetcher(test_server)
        extractor = Extractor()
        frontier = URLFrontier()
        pagination = PaginationHandler(fetcher)

        orchestrator = CrawlOrchestrator(
            config=config,
            fetcher=fetcher,
            extractor=extractor,
            frontier=frontier,
            pagination_handler=pagination,
        )

        records = await orchestrator.crawl()
        await fetcher.close()

        # Item 3 is only on region-a page 2, so pagination must be working
        names = {r["name"] for r in records}
        assert "Gamma LLC" in names

    @pytest.mark.asyncio
    async def test_deduplication(self, test_server):
        config = _make_crawl_config(test_server)
        fetcher = MockHttpFetcher(test_server)
        extractor = Extractor()
        frontier = URLFrontier()
        pagination = PaginationHandler(fetcher)

        orchestrator = CrawlOrchestrator(
            config=config,
            fetcher=fetcher,
            extractor=extractor,
            frontier=frontier,
            pagination_handler=pagination,
        )

        records = await orchestrator.crawl()
        await fetcher.close()

        # Each detail URL should appear only once
        source_urls = [r["_source_url"] for r in records]
        assert len(source_urls) == len(set(source_urls))

    @pytest.mark.asyncio
    async def test_404_handled_gracefully(self, test_server):
        config = _make_crawl_config(test_server)
        # Add a level that will produce a 404
        config.levels[1].link_selector = "a.listing-link"

        fetcher = MockHttpFetcher(test_server)
        extractor = Extractor()
        frontier = URLFrontier()
        pagination = PaginationHandler(fetcher)

        # Manually add a URL that will 404
        frontier.add(f"{test_server}/detail/missing", depth=2, ancestors=[
            {"level": "homepage", "label": None, "url": f"{test_server}/directory"},
            {"level": "region", "label": "Region A", "url": f"{test_server}/directory/region-a"},
        ])

        orchestrator = CrawlOrchestrator(
            config=config,
            fetcher=fetcher,
            extractor=extractor,
            frontier=frontier,
            pagination_handler=pagination,
        )

        records = await orchestrator.crawl()
        await fetcher.close()

        # Should still get 4 records from valid URLs, 404 is skipped
        assert len(records) == 4
