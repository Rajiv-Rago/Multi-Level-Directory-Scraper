"""HTML field extraction, link extraction, and context extraction using BeautifulSoup."""

from __future__ import annotations

from bs4 import BeautifulSoup


class Extractor:
    """Extracts structured data from HTML using CSS selectors."""

    def extract_field(
        self, html: str, selectors: list[str], *, attribute: str | None = None
    ) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        for selector in selectors:
            element = soup.select_one(selector)
            if element is not None:
                if attribute:
                    return element.get(attribute)
                return element.get_text(strip=True)
        return None

    def extract_record(
        self, html: str, fields_config: list[dict], ancestors: list[dict]
    ) -> dict:
        record: dict = {}
        for field in fields_config:
            record[field["name"]] = self.extract_field(
                html,
                field["selectors"],
                attribute=field.get("attribute"),
            )
        record["_ancestors"] = ancestors
        return record

    def extract_links(self, html: str, link_selector: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        return [
            a["href"]
            for a in soup.select(link_selector)
            if a.get("href")
        ]

    def extract_context(self, html: str, context_selector: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        element = soup.select_one(context_selector)
        if element is not None:
            return element.get_text(strip=True)
        return None
