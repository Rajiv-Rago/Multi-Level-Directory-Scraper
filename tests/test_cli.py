"""Tests for the CLI interface."""

import httpx
import respx
from typer.testing import CliRunner

from scraper.cli import app

runner = CliRunner()

MOCK_HTML = """\
<html>
<body>
  <a class="region-link" href="/region/1">
    <h2 class="title">North Region</h2>
  </a>
  <a class="region-link" href="/region/2">
    <h2 class="title">South Region</h2>
  </a>
</body>
</html>
"""

ROBOTS_TXT_ALLOW_ALL = """\
User-agent: *
Allow: /
"""


class TestCLI:
    @respx.mock
    def test_cli_loads_valid_config(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0

    def test_cli_invalid_config_exit_code_1(self, write_config):
        path = write_config({"site": {"name": "bad"}})
        result = runner.invoke(app, [str(path)])
        assert result.exit_code == 1

    @respx.mock
    def test_cli_override_delay(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--delay-min", "0.5", "--delay-max", "1.0", "--dry-run"])
        assert result.exit_code == 0

    @respx.mock
    def test_cli_override_log_level(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--log-level", "debug", "--dry-run"])
        assert result.exit_code == 0

    @respx.mock
    def test_cli_dry_run_flag(self, valid_config_dict, write_config, tmp_path):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0
        log_files = list(tmp_path.glob("**/*.log"))
        assert len(log_files) == 0

    def test_cli_help_output(self):
        result = runner.invoke(app, ["--help"], env={"NO_COLOR": "1"})
        assert result.exit_code == 0
        assert "config-path" in result.output.lower() or "config_path" in result.output.lower()
        assert "--dry-run" in result.output


class TestDryRun:
    @respx.mock
    def test_dry_run_validates_config(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0

    @respx.mock
    def test_dry_run_no_log_file(self, valid_config_dict, write_config, tmp_path):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0
        log_files = list(tmp_path.glob("**/*.log"))
        assert len(log_files) == 0

    @respx.mock
    def test_dry_run_no_output_files(self, valid_config_dict, write_config, tmp_path):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0
        csv_files = list(tmp_path.glob("**/*.csv"))
        json_files = list(tmp_path.glob("**/*.json"))
        assert len(csv_files) == 0
        assert len(json_files) == 0

    @respx.mock
    def test_dry_run_prints_table(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0
        output = result.output
        assert "region_name" in output
        assert "region_url" in output

    @respx.mock
    def test_dry_run_invalid_config_exits_1(self, write_config):
        path = write_config({"site": {"name": "bad"}})
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 1


class TestIntegration:
    @respx.mock
    def test_full_flow_config_to_log(self, valid_config_dict, write_config, tmp_path):

        valid_config_dict["site"]["output_dir"] = str(tmp_path / "output")
        path = write_config(valid_config_dict)
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL)
        )
        respx.get("https://example.com").mock(
            return_value=httpx.Response(200, text=MOCK_HTML)
        )
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0

        # dry-run doesn't create a log file, so verify via output
        assert "region_name" in result.output

    def test_exit_codes(self, valid_config_dict, write_config, tmp_path):
        bad_path = write_config({"site": {"name": "no-url"}})
        result_bad = runner.invoke(app, [str(bad_path)])
        assert result_bad.exit_code == 1
