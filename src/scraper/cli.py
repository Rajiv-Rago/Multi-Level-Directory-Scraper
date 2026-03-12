"""CLI entry point for the scraper."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from scraper.config import apply_overrides, load_config
from scraper.logging import setup_logging

app = typer.Typer(name="scraper", add_completion=False)


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
        logger.info("dry_run", message="Config validated successfully")
        raise typer.Exit(0)

    raise typer.Exit(0)
