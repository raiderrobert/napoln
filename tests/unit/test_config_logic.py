"""Tests for napoln.commands.config — configuration logic."""

from __future__ import annotations

import pytest

from napoln.commands.config import _parse_config_value


class TestParseConfigValue:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("true", True),
            ("True", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("no", False),
        ],
        ids=["true-lower", "true-title", "yes-lower", "false-lower", "false-title", "no-lower"],
    )
    def test_booleans(self, raw, expected):
        assert _parse_config_value(raw) is expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("0", 0),
            ("42", 42),
        ],
        ids=["zero", "positive"],
    )
    def test_integers(self, raw, expected):
        result = _parse_config_value(raw)
        assert result == expected
        assert isinstance(result, int)

    def test_comma_separated_list(self):
        assert _parse_config_value("claude-code, pi, codex") == ["claude-code", "pi", "codex"]

    def test_comma_no_spaces(self):
        assert _parse_config_value("a,b,c") == ["a", "b", "c"]

    def test_plain_string(self):
        assert _parse_config_value("project") == "project"

    def test_mixed_alphanumeric_is_string(self):
        assert _parse_config_value("v1") == "v1"

    def test_negative_number_is_string(self):
        """isdigit() returns False for negatives."""
        assert _parse_config_value("-1") == "-1"
