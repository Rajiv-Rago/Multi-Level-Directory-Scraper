"""Tests for the CLI interface."""

from typer.testing import CliRunner

from scraper.cli import app

runner = CliRunner()


class TestCLI:
    def test_cli_loads_valid_config(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        result = runner.invoke(app, [str(path)])
        assert result.exit_code == 0

    def test_cli_invalid_config_exit_code_1(self, write_config):
        path = write_config({"site": {"name": "bad"}})
        result = runner.invoke(app, [str(path)])
        assert result.exit_code == 1

    def test_cli_override_delay(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        result = runner.invoke(app, [str(path), "--delay-min", "0.5", "--delay-max", "1.0"])
        assert result.exit_code == 0

    def test_cli_override_log_level(self, valid_config_dict, write_config):
        path = write_config(valid_config_dict)
        result = runner.invoke(app, [str(path), "--log-level", "debug"])
        assert result.exit_code == 0

    def test_cli_dry_run_flag(self, valid_config_dict, write_config, tmp_path):
        path = write_config(valid_config_dict)
        result = runner.invoke(app, [str(path), "--dry-run"])
        assert result.exit_code == 0
        log_files = list(tmp_path.glob("**/*.log"))
        assert len(log_files) == 0

    def test_cli_help_output(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "config-path" in result.output.lower() or "config_path" in result.output.lower()
        assert "--dry-run" in result.output
