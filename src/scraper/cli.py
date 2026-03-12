"""CLI entry point for the scraper."""

import typer

app = typer.Typer(name="scraper", add_completion=False)


@app.command()
def main() -> None:
    """Multi-level directory scraper."""
    raise typer.Exit(0)
