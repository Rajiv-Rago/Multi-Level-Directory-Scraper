"""CLI entry point for the scraper."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from scraper.config import ScrapeConfig, apply_overrides, load_config
from scraper.logging import setup_logging

app = typer.Typer(name="scraper", add_completion=False)


def _build_crawl_config(config: ScrapeConfig):
    """Convert Pydantic config to orchestrator's CrawlConfig."""
    from scraper.orchestrator import CrawlConfig, LevelConfig
    from scraper.pagination import PaginationConfig

    levels = []
    for i, level in enumerate(config.levels):
        is_detail = (i == len(config.levels) - 1) or level.link_selector is None

        pagination = None
        if level.pagination and level.pagination.type != "none":
            pagination = PaginationConfig(
                type=level.pagination.type,
                selector=level.pagination.selector or "",
                max_pages=level.pagination.max_pages,
            )

        fields = [
            {"name": f.name, "selectors": [s.strip() for s in f.selector.split(",")], "attribute": f.attribute if f.attribute != "text" else None}
            for f in level.fields
        ] if is_detail else None

        levels.append(LevelConfig(
            depth=level.depth,
            name=level.name,
            link_selector=level.link_selector,
            context_selector=level.context_selector,
            wait_selector=level.wait_selector,
            renderer=level.renderer,
            pagination=pagination,
            fields=fields,
            is_detail=is_detail,
        ))

    return CrawlConfig(
        base_url=config.site.base_url,
        levels=levels,
        delay=config.site.request_delay.min,
        max_pages_per_level=config.site.max_pages,
    )


def _records_to_models(raw_records: list[dict], config: ScrapeConfig) -> list:
    """Convert orchestrator's raw dicts to DirectoryRecord models."""
    from models.record import DirectoryRecord

    results = []
    for raw in raw_records:
        ancestors = raw.get("_ancestors", [])
        region = ancestors[0]["label"] if len(ancestors) > 0 and ancestors[0].get("label") else "Unknown"
        category = ancestors[1]["label"] if len(ancestors) > 1 and ancestors[1].get("label") else region

        results.append(DirectoryRecord(
            region=region,
            category=category,
            name=raw.get("name") or "Unknown",
            address=raw.get("address"),
            phone=raw.get("phone"),
            website=raw.get("website"),
            description=raw.get("description"),
            source_url=raw.get("_source_url", ""),
            scraped_at=datetime.now(UTC),
        ))

    return results


async def run_crawl(config: ScrapeConfig, logger, resume_state: dict | None = None) -> int:
    """Run the full crawl pipeline: fetch → extract → clean → export."""
    import random

    from scraper.checkpoint import CheckpointManager
    from scraper.checkpoint import config_hash as compute_config_hash
    from scraper.extractor import Extractor
    from scraper.fetcher import HttpxFetcher, PlaywrightFetcher
    from scraper.frontier import URLFrontier
    from scraper.orchestrator import CrawlOrchestrator
    from scraper.pagination import PaginationHandler
    from scraper.politeness import PolitenessController
    from scraper.retry import with_retry
    from scraper.signals import SignalHandler

    output_path = Path(config.site.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    crawl_config = _build_crawl_config(config)

    needs_browser = any(level.renderer == "browser" for level in config.levels)

    if needs_browser:
        fetcher = PlaywrightFetcher()
        await fetcher.start()
        logger.info("fetcher_started", type="playwright")
    else:
        fetcher = HttpxFetcher()
        logger.info("fetcher_started", type="httpx")

    fetcher.fetch = with_retry(fetcher.fetch)

    extractor = Extractor()
    frontier = URLFrontier()
    pagination = PaginationHandler(fetcher)

    politeness = PolitenessController(config, logger)
    await politeness.initialize()

    delay_min = config.site.request_delay.min
    delay_max = config.site.request_delay.max

    async def delay_fn():
        wait = random.uniform(delay_min, delay_max)
        await asyncio.sleep(wait)

    orchestrator = CrawlOrchestrator(
        config=crawl_config,
        fetcher=fetcher,
        extractor=extractor,
        frontier=frontier,
        pagination_handler=pagination,
        delay_fn=delay_fn,
    )

    cfg_hash = compute_config_hash({"base_url": config.site.base_url, "levels": len(config.levels)})
    checkpoint_mgr = CheckpointManager(output_dir=output_path, config_hash=cfg_hash)

    records_so_far: list[dict] = []

    def get_state():
        return {
            "visited_urls": frontier._visited,
            "pending_urls": [],
            "records_extracted": len(records_so_far),
        }

    def flush_results():
        if records_so_far:
            models = _records_to_models(records_so_far, config)
            from export.csv_export import export_csv
            export_csv(models, output_path / "data_partial.csv")
            logger.info("partial_results_flushed", records=len(models))

    signal_handler = SignalHandler(checkpoint_mgr, get_state, flush_results)
    signal_handler.register()

    try:
        logger.info("crawl_started", base_url=config.site.base_url)
        raw_records = await orchestrator.crawl()
        records_so_far.extend(raw_records)
    except KeyboardInterrupt:
        logger.info("crawl_interrupted")
    finally:
        await fetcher.close()

    if not records_so_far:
        logger.warning("no_records_extracted")
        return 1

    logger.info("extraction_complete", raw_records=len(records_so_far))

    models = _records_to_models(records_so_far, config)

    from pipeline import run_pipeline
    pipeline_config = {
        "default_country_code": "US",
        "base_url": config.site.base_url,
    }
    cleaned_records, collector = run_pipeline(models, pipeline_config, output_path)

    checkpoint_mgr.cleanup()
    logger.info("crawl_complete", total_records=len(cleaned_records))

    return 0


async def run_dry_run(config: ScrapeConfig, logger) -> int:
    """Fetch level-0 page, apply selectors, print extraction results table."""
    import httpx
    from bs4 import BeautifulSoup

    from scraper.politeness import PolitenessController

    controller = PolitenessController(config, logger)
    await controller.initialize()

    total_fields = 0
    extracted_fields = 0
    rows: list[tuple[str, str, str, str]] = []

    for level in config.levels:
        if level.depth > 0:
            logger.info(
                "dry_run_skip_level",
                level=level.name,
                depth=level.depth,
                message=f"Level '{level.name}' (depth {level.depth}): selector validation requires crawl engine (Phase 2)",
            )
            continue

        url = config.site.base_url
        if not controller.is_allowed(url):
            logger.warning("dry_run_url_blocked", url=url)
            continue

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "multi-level-directory-scraper"})

        soup = BeautifulSoup(response.text, "lxml")

        for field in level.fields:
            total_fields += 1
            elements = soup.select(field.selector)
            if elements:
                if field.attribute == "text":
                    value = elements[0].get_text(strip=True)
                else:
                    value = elements[0].get(field.attribute, "NOT FOUND")
                if value:
                    extracted_fields += 1
                else:
                    value = field.default or "NOT FOUND"
            else:
                value = field.default or "NOT FOUND"
                if field.default:
                    extracted_fields += 1

            rows.append((level.name, field.name, field.selector, str(value)))

    _print_table(rows, logger)
    logger.info("dry_run_summary", extracted=extracted_fields, total=total_fields)

    if total_fields == 0:
        return 1

    level_names = {r[0] for r in rows}
    for level_name in level_names:
        level_rows = [r for r in rows if r[0] == level_name]
        level_extracted = sum(1 for r in level_rows if r[3] != "NOT FOUND")
        if level_extracted == 0:
            return 1

    return 0


def _print_table(rows: list[tuple[str, str, str, str]], logger) -> None:
    """Print extraction results as a formatted table."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Dry-Run Extraction Results")
        table.add_column("Level", style="cyan")
        table.add_column("Field", style="green")
        table.add_column("Selector", style="yellow")
        table.add_column("Value", style="white")

        for level, field, selector, value in rows:
            style = "red" if value == "NOT FOUND" else None
            table.add_row(level, field, selector, value, style=style)

        console.print(table)
    except ImportError:
        header = f"{'Level':<15} {'Field':<20} {'Selector':<25} {'Value'}"
        print(header)
        print("-" * len(header))
        for level, field, selector, value in rows:
            print(f"{level:<15} {field:<20} {selector:<25} {value}")


@app.command()
def main(
    config_path: Annotated[Path, typer.Argument(help="Path to YAML config file")],
    output_dir: Annotated[str | None, typer.Option("--output-dir", help="Override output directory")] = None,
    delay_min: Annotated[float | None, typer.Option("--delay-min", help="Minimum request delay (seconds)")] = None,
    delay_max: Annotated[float | None, typer.Option("--delay-max", help="Maximum request delay (seconds)")] = None,
    max_pages: Annotated[int | None, typer.Option("--max-pages", help="Maximum pages per level")] = None,
    log_level: Annotated[str | None, typer.Option("--log-level", help="Log level: debug/info/warning")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate config and test selectors without full crawl")] = False,
    resume: Annotated[bool, typer.Option("--resume", help="Resume from checkpoint if available")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force resume even with config mismatch")] = False,
) -> None:
    """Multi-level directory scraper."""
    config = load_config(config_path)

    overrides = {
        "output_dir": output_dir,
        "delay_min": delay_min,
        "delay_max": delay_max,
        "max_pages": max_pages,
        "log_level": log_level,
    }
    config = apply_overrides(config, overrides)

    log_file = None if dry_run else Path(config.site.output_dir) / "scrape.log"
    logger = setup_logging(config.site.log_level, log_file)

    logger.info("config_loaded", site=config.site.name, levels=len(config.levels))

    if dry_run:
        exit_code = asyncio.run(run_dry_run(config, logger))
        raise typer.Exit(exit_code)

    resume_state = None
    if resume:
        from scraper.checkpoint import CheckpointManager
        from scraper.checkpoint import config_hash as compute_config_hash

        output_path = Path(config.site.output_dir)
        cfg_hash = compute_config_hash({"base_url": config.site.base_url, "levels": len(config.levels)})
        checkpoint_mgr = CheckpointManager(output_dir=output_path, config_hash=cfg_hash)

        resume_state = checkpoint_mgr.load(force=force)
        if resume_state:
            logger.info(
                "checkpoint_resumed",
                visited=len(resume_state.get("visited_urls", set())),
                pending=len(resume_state.get("pending_urls", [])),
            )
        else:
            logger.warning("no_valid_checkpoint", message="No valid checkpoint found, starting fresh")

    exit_code = asyncio.run(run_crawl(config, logger, resume_state))
    raise typer.Exit(exit_code)
