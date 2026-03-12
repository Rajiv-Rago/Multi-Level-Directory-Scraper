"""Tests for URL normalization."""

from scraper.frontier import normalize_url


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/path/") == "https://example.com/path"

    def test_preserves_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"

    def test_sorts_query_params(self):
        assert normalize_url("https://example.com/search?b=2&a=1") == "https://example.com/search?a=1&b=2"

    def test_removes_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_removes_default_https_port(self):
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_removes_default_http_port(self):
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_preserves_non_default_port(self):
        assert normalize_url("https://example.com:8080/path") == "https://example.com:8080/path"

    def test_already_normalized_unchanged(self):
        url = "https://example.com/path?a=1&b=2"
        assert normalize_url(url) == url
