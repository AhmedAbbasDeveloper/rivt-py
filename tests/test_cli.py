"""Tests for CLI commands."""

import subprocess
import sys
from pathlib import Path


def _run_rivt(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "rivt", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


class TestNewRule:
    def test_creates_rule_file(self, tmp_path: Path) -> None:
        result = _run_rivt("new-rule", "handle-db-errors", cwd=tmp_path)
        assert result.returncode == 0

        rule_file = tmp_path / ".rivt" / "rules" / "handle_db_errors.py"
        assert rule_file.is_file()
        content = rule_file.read_text()
        assert "class HandleDbErrorsRule(Rule):" in content
        assert 'id = "handle-db-errors"' in content
        assert "from rivt import Rule, RivtConfig, Violation" in content

    def test_refuses_existing_file(self, tmp_path: Path) -> None:
        _run_rivt("new-rule", "my-rule", cwd=tmp_path)
        result = _run_rivt("new-rule", "my-rule", cwd=tmp_path)
        assert result.returncode == 1
        assert "already exists" in result.stderr

    def test_creates_directory(self, tmp_path: Path) -> None:
        assert not (tmp_path / ".rivt").exists()
        _run_rivt("new-rule", "test-rule", cwd=tmp_path)
        assert (tmp_path / ".rivt" / "rules").is_dir()


class TestInit:
    def test_refuses_if_already_configured(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.rivt]\nconfig_module = 'x'\n")
        result = _run_rivt("init", cwd=tmp_path)
        assert result.returncode == 1
        assert "already configured" in result.stderr


class TestCheck:
    def test_clean_project(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.rivt]\n")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("print('hello')\n")
        result = _run_rivt("check", cwd=tmp_path)
        assert result.returncode == 0
        assert "No violations found" in result.stdout

    def test_no_config_exits_2(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        result = _run_rivt("check", cwd=tmp_path)
        assert result.returncode == 2
