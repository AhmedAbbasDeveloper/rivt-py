"""Tests for runner: suppression and syntax error reporting."""

from pathlib import Path
from unittest.mock import patch

from rivt.models import RivtConfig, Violation
from rivt.runner import (
    _file_disabled_rules,
    _is_inline_suppressed,
    _next_line_disabled_rules,
)


class TestInlineSuppression:
    def test_suppressed(self) -> None:
        lines = ["from foo import bar  # rivt: disable=test-rule"]
        v = Violation(rule_id="test-rule", path="a.py", line=1, col=0, message="m")
        assert _is_inline_suppressed(v, lines) is True

    def test_not_suppressed(self) -> None:
        lines = ["from foo import bar"]
        v = Violation(rule_id="test-rule", path="a.py", line=1, col=0, message="m")
        assert _is_inline_suppressed(v, lines) is False

    def test_different_rule_not_suppressed(self) -> None:
        lines = ["from foo import bar  # rivt: disable=other-rule"]
        v = Violation(rule_id="test-rule", path="a.py", line=1, col=0, message="m")
        assert _is_inline_suppressed(v, lines) is False

    def test_multiple_rules_suppressed(self) -> None:
        lines = ["from foo import bar  # rivt: disable=test-rule,other-rule"]
        v = Violation(rule_id="test-rule", path="a.py", line=1, col=0, message="m")
        assert _is_inline_suppressed(v, lines) is True


class TestFileDisable:
    def test_file_level_disable(self) -> None:
        lines = ["# rivt: disable-file=test-rule", "import os"]
        assert "test-rule" in _file_disabled_rules(lines)

    def test_file_level_multiple(self) -> None:
        lines = ["# rivt: disable-file=rule-a,rule-b", "import os"]
        disabled = _file_disabled_rules(lines)
        assert "rule-a" in disabled
        assert "rule-b" in disabled

    def test_file_level_only_first_10_lines(self) -> None:
        lines = [""] * 11 + ["# rivt: disable-file=test-rule"]
        assert "test-rule" not in _file_disabled_rules(lines)


class TestNextLineDisable:
    def test_next_line_suppression(self) -> None:
        lines = ["# rivt: disable-next-line=test-rule", "from foo import bar"]
        disabled = _next_line_disabled_rules(lines)
        assert 2 in disabled
        assert "test-rule" in disabled[2]

    def test_next_line_does_not_affect_other_lines(self) -> None:
        lines = ["# rivt: disable-next-line=test-rule", "line2", "line3"]
        disabled = _next_line_disabled_rules(lines)
        assert 3 not in disabled


class TestSyntaxErrorReporting:
    def test_syntax_error_reported(self, tmp_path: Path) -> None:
        config = RivtConfig()
        py_file = tmp_path / "broken.py"
        py_file.write_text("def foo(\n")

        (tmp_path / "pyproject.toml").write_text("[tool.rivt]\n")

        with patch("rivt.runner.load_plugin_rules", return_value=[]):
            from rivt.runner import run_checks

            violations = run_checks(tmp_path, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "parse-error"
        assert "Failed to parse" in violations[0].message
