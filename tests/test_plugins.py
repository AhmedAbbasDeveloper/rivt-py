"""Tests for plugin discovery and loading."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rivt.models import Layer, RivtConfig, RivtError
from rivt.plugins import load_plugin_rules
from rivt.runner import find_python_files, run_checks


def _rule_source(rule_id: str, *, violation: bool = True) -> str:
    body = (
        "return [Violation("
        f'rule_id="{rule_id}", '
        "path=str(fp), line=1, col=0, message='test')]"
        if violation
        else "return []"
    )
    return (
        "import ast\n"
        "from pathlib import Path\n"
        "from rivt import Rule, RivtConfig, Violation\n"
        f"class TestRule(Rule):\n"
        f'    id = "{rule_id}"\n'
        f'    description = "{rule_id}"\n'
        "    def check(self, tree: ast.Module,"
        " fp: Path, c: RivtConfig"
        ") -> list[Violation]:\n"
        f"        {body}\n"
    )


class TestLocalDiscovery:
    def test_loads_from_rivt_rules(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "my_rule.py").write_text(_rule_source("my-rule"))

        rules = load_plugin_rules(tmp_path, [])
        assert len(rules) == 1
        assert rules[0].id == "my-rule"

    def test_skips_underscore_files(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "_helpers.py").write_text("UTILITY = True\n")
        (rules_dir / "my_rule.py").write_text(_rule_source("my-rule"))

        rules = load_plugin_rules(tmp_path, [])
        assert len(rules) == 1

    def test_syntax_error_raises(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "bad.py").write_text("def broken(\n")

        with pytest.raises(RivtError):
            load_plugin_rules(tmp_path, [])

    def test_no_rules_dir(self, tmp_path: Path) -> None:
        rules = load_plugin_rules(tmp_path, [])
        assert rules == []


class TestValidation:
    def test_rejects_builtin_id(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "layer.py").write_text(_rule_source("layer-imports"))

        with pytest.raises(RivtError):
            load_plugin_rules(tmp_path, [])

    def test_rejects_duplicate_ids(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule_a.py").write_text(_rule_source("my-rule"))
        (rules_dir / "rule_b.py").write_text(_rule_source("my-rule"))

        with pytest.raises(RivtError):
            load_plugin_rules(tmp_path, [])


class TestEntryPoints:
    def test_loads_from_entry_points(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)

        mock_rule = MagicMock()
        mock_rule.id = "ep-rule"
        mock_rule.description = "ep-rule"

        mock_ep = MagicMock()
        mock_ep.name = "test_plugin"
        mock_ep.value = "test_module:get_rules"
        mock_ep.load.return_value = lambda: [mock_rule]

        with patch(
            "rivt.plugins.importlib.metadata.entry_points", return_value=[mock_ep]
        ):
            rules = load_plugin_rules(tmp_path, [])
        assert len(rules) == 1


class TestIntegration:
    def test_rivt_dir_excluded_from_file_discovery(self, tmp_path: Path) -> None:
        config = RivtConfig()
        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "my_rule.py").write_text(_rule_source("my-rule"))

        (tmp_path / "app.py").write_text("x = 1\n")

        files = find_python_files(tmp_path, config)
        assert all(".rivt" not in str(f) for f in files)

    def test_custom_rule_runs_with_check(self, tmp_path: Path) -> None:
        config = RivtConfig(
            layers={"routers": Layer(name="routers", paths=["app"])},
        )

        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "always_fail.py").write_text(_rule_source("always-fail"))

        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "main.py").write_text("x = 1\n")

        violations = run_checks(tmp_path, config)
        custom_violations = [v for v in violations if v.rule_id == "always-fail"]
        assert len(custom_violations) == 1

    def test_disable_custom_rule(self, tmp_path: Path) -> None:
        config = RivtConfig(disable=["always-fail"])

        rules_dir = tmp_path / ".rivt" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "always_fail.py").write_text(_rule_source("always-fail"))

        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "main.py").write_text("x = 1\n")

        violations = run_checks(tmp_path, config)
        custom_violations = [v for v in violations if v.rule_id == "always-fail"]
        assert len(custom_violations) == 0
