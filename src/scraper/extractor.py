"""HTML field extraction, link extraction, and context extraction using BeautifulSoup."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def get_base_url(html: str, page_url: str) -> str:
    """Return the effective base URL for resolving relative hrefs.

    Uses the <base href="..."> tag if present, otherwise falls back to page_url.
    """
    soup = BeautifulSoup(html, "lxml")
    base_tag = soup.find("base", href=True)
    if base_tag:
        return base_tag["href"]
    return page_url


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

    def extract_links(self, html: str, link_selector: str, page_url: str | None = None) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        hrefs = [a["href"] for a in soup.select(link_selector) if a.get("href")]
        if page_url is None:
            return hrefs
        base_url = get_base_url(html, page_url)
        return [urljoin(base_url, href) for href in hrefs]

    def extract_context(self, html: str, context_selector: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        element = soup.select_one(context_selector)
        if element is not None:
            return element.get_text(strip=True)
        return None
