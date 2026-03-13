"""Tests for HTML field extraction, link extraction, and context extraction."""


from scraper.extractor import Extractor


SAMPLE_HTML = """
<html><body>
  <h1 class="name">Acme Corp</h1>
  <span class="address">123 Main St</span>
  <span class="phone">(555) 123-4567</span>
  <a class="website" href="https://acme.com">Visit Website</a>
  <span class="rating">4.5 &amp; up</span>
  <span class="  spaced  ">  padded text  </span>
</body></html>
"""

LINKS_HTML = """
<html><body>
  <a class="listing" href="/detail/1">Item 1</a>
  <a class="listing" href="/detail/2">Item 2</a>
  <a class="listing">No href</a>
  <a class="other" href="/other">Other</a>
</body></html>
"""

CONTEXT_HTML = """
<html><body>
  <h2 class="region-title">North Region</h2>
  <div class="listings">...</div>
</body></html>
"""


class TestExtractField:
    def setup_method(self):
        self.extractor = Extractor()

    def test_single_selector_match(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["h1.name"])
        assert result == "Acme Corp"

    def test_fallback_selector(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["h1.missing", "span.address"])
        assert result == "123 Main St"

    def test_all_selectors_miss_returns_none(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["div.nonexistent", "p.also-missing"])
        assert result is None

    def test_attribute_extraction(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["a.website"], attribute="href")
        assert result == "https://acme.com"

    def test_html_entities_decoded(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["span.rating"])
        assert result == "4.5 & up"

    def test_whitespace_stripped(self):
        result = self.extractor.extract_field(SAMPLE_HTML, ["span.spaced"])
        assert result == "padded text"


class TestExtractRecord:
    def setup_method(self):
        self.extractor = Extractor()

    def test_all_fields_present(self):
        fields_config = [
            {"name": "name", "selectors": ["h1.name"]},
            {"name": "address", "selectors": ["span.address"]},
            {"name": "phone", "selectors": ["span.phone"]},
        ]
        record = self.extractor.extract_record(SAMPLE_HTML, fields_config, [])
        assert record["name"] == "Acme Corp"
        assert record["address"] == "123 Main St"
        assert record["phone"] == "(555) 123-4567"

    def test_missing_fields_are_none(self):
        fields_config = [
            {"name": "name", "selectors": ["h1.name"]},
            {"name": "email", "selectors": ["span.email"]},
        ]
        record = self.extractor.extract_record(SAMPLE_HTML, fields_config, [])
        assert record["name"] == "Acme Corp"
        assert record["email"] is None

    def test_fallback_selectors_in_record(self):
        fields_config = [
            {"name": "contact", "selectors": ["span.email", "span.phone"]},
        ]
        record = self.extractor.extract_record(SAMPLE_HTML, fields_config, [])
        assert record["contact"] == "(555) 123-4567"

    def test_ancestors_included_in_record(self):
        fields_config = [{"name": "name", "selectors": ["h1.name"]}]
        ancestors = [
            {"level": "region", "label": "North", "url": "https://example.com/north"},
            {"level": "category", "label": "Restaurants", "url": "https://example.com/north/restaurants"},
        ]
        record = self.extractor.extract_record(SAMPLE_HTML, fields_config, ancestors)
        assert record["_ancestors"] == ancestors

    def test_attribute_extraction_in_record(self):
        fields_config = [
            {"name": "website", "selectors": ["a.website"], "attribute": "href"},
        ]
        record = self.extractor.extract_record(SAMPLE_HTML, fields_config, [])
        assert record["website"] == "https://acme.com"


class TestExtractLinks:
    def setup_method(self):
        self.extractor = Extractor()

    def test_extracts_matching_hrefs(self):
        links = self.extractor.extract_links(LINKS_HTML, "a.listing")
        assert links == ["/detail/1", "/detail/2"]

    def test_empty_when_no_match(self):
        links = self.extractor.extract_links(LINKS_HTML, "a.nonexistent")
        assert links == []

    def test_skips_anchors_without_href(self):
        links = self.extractor.extract_links(LINKS_HTML, "a.listing")
        assert "/detail/1" in links
        assert "/detail/2" in links
        assert len(links) == 2


class TestExtractContext:
    def setup_method(self):
        self.extractor = Extractor()

    def test_returns_matching_text(self):
        result = self.extractor.extract_context(CONTEXT_HTML, "h2.region-title")
        assert result == "North Region"

    def test_returns_none_when_no_match(self):
        result = self.extractor.extract_context(CONTEXT_HTML, "h2.missing")
        assert result is None
