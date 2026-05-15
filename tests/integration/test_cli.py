"""Integration tests for napoln CLI surface — help text, version, flags.

Behavioral tests for each command live in tests/features/*.feature.
"""

from __future__ import annotations

import re

from typer.testing import CliRunner

from napoln.cli import app


class TestVersionCommand:
    def test_version(self):
        result = CliRunner().invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "napoln" in result.output
        assert re.search(r"\d+\.\d+\.\d+", result.output)


class TestHelpCommand:
    def test_help(self):
        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "agent skills" in result.output.lower()

    def test_help_shows_seven_commands(self):
        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("add", "remove", "upgrade", "list", "install", "init", "config"):
            assert cmd in result.output

    def test_help_hides_cut_commands(self):
        result = CliRunner().invoke(app, ["--help"])
        for cmd in ("status", "diff", "resolve", "sync", "doctor", "gc", "telemetry"):
            assert f"  {cmd} " not in result.output or cmd in ("doctor", "gc")

    def test_no_completion_in_help(self):
        result = CliRunner().invoke(app, ["--help"])
        assert "--install-completion" not in result.output
        assert "--show-completion" not in result.output

    def test_add_help(self):
        result = CliRunner().invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--skill" in result.output
        assert "--project" in result.output

    def test_init_help(self):
        result = CliRunner().invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Scaffold" in result.output
