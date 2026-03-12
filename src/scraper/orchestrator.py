"""Crawl orchestrator: level-based BFS tying frontier, fetcher, extractor, and pagination together."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

import structlog

from scraper.extractor import Extractor
from scraper.frontier import URLFrontier
from scraper.pagination import PaginationConfig, PaginationHandler

logger = structlog.get_logger()


@dataclass
class LevelConfig:
    depth: int
    name: str
    link_selector: str | None = None
    context_selector: str | None = None
    wait_selector: str | None = None
    renderer: str = "static"
    pagination: PaginationConfig | None = None
    fields: list[dict] | None = None
    is_detail: bool = False


@dataclass
class CrawlConfig:
    base_url: str
    levels: list[LevelConfig]
    delay: float = 1.0


class CrawlOrchestrator:
    """Level-based BFS crawl orchestrator."""

    def __init__(
        self,
        config: CrawlConfig,
        fetcher,
        extractor: Extractor,
        frontier: URLFrontier,
        pagination_handler: PaginationHandler,
        delay_fn=None,
    ) -> None:
        self._config = config
        self._fetcher = fetcher
        self._extractor = extractor
        self._frontier = frontier
        self._pagination = pagination_handler
        self._delay_fn = delay_fn

    async def crawl(self) -> list[dict]:
        records: list[dict] = []
        self._frontier.add(self._config.base_url, depth=0)

        for level in self._config.levels:
            level_records = 0
            level_urls = 0

            while self._frontier.has_pending(level.depth):
                item = self._frontier.pop(level.depth)
                level_urls += 1

                html = await self._fetch(item.url, level)
                if html is None:
                    logger.warning("fetch_failed_skipping", url=item.url, depth=level.depth)
                    continue

                pages = await self._pagination.paginate(html, level.pagination, item.url)

                for page_html in pages:
                    if level.is_detail:
                        record = self._extractor.extract_record(
                            page_html, level.fields or [], item.ancestors
                        )
                        record["_source_url"] = item.url
                        records.append(record)
                        level_records += 1
                    else:
                        links = self._extractor.extract_links(
                            page_html, level.link_selector
                        )
                        context_label = None
                        if level.context_selector:
                            context_label = self._extractor.extract_context(
                                page_html, level.context_selector
                            )
                        ancestors = item.ancestors + [
                            {"level": level.name, "label": context_label, "url": item.url}
                        ]
                        for link in links:
                            absolute_url = urljoin(item.url, link)
                            self._frontier.add(absolute_url, level.depth + 1, ancestors)

                if self._delay_fn:
                    await self._delay_fn()

            logger.info(
                "level_complete",
                level=level.name,
                depth=level.depth,
                urls_processed=level_urls,
                records_extracted=level_records,
            )

        logger.info(
            "crawl_complete",
            total_records=len(records),
            total_urls=self._frontier.visited_count,
        )
        return records

    async def _fetch(self, url: str, level: LevelConfig) -> str | None:
        try:
            return await self._fetcher.fetch(
                url,
                wait_selector=level.wait_selector,
                timeout=15.0,
            )
        except Exception:
            logger.exception("fetch_error", url=url)
            return None
