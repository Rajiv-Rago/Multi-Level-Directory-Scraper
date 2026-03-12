"""CLI entry point for the scraper."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from scraper.config import ScrapeConfig, apply_overrides, load_config
from scraper.logging import setup_logging

app = typer.Typer(name="scraper", add_completion=False)


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
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", help="Override output directory")] = None,
    delay_min: Annotated[Optional[float], typer.Option("--delay-min", help="Minimum request delay (seconds)")] = None,
    delay_max: Annotated[Optional[float], typer.Option("--delay-max", help="Maximum request delay (seconds)")] = None,
    max_pages: Annotated[Optional[int], typer.Option("--max-pages", help="Maximum pages per level")] = None,
    log_level: Annotated[Optional[str], typer.Option("--log-level", help="Log level: debug/info/warning")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate config and test selectors without full crawl")] = False,
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

    raise typer.Exit(0)
