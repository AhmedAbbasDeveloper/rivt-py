from __future__ import annotations

import ast
import re
from fnmatch import fnmatch
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.plugins import load_plugin_rules
from rivt.rules import ALL_RULES

ALWAYS_EXCLUDE = {
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "__pycache__",
    ".tox",
    ".eggs",
    ".rivt",
    "build",
    "dist",
}

_DISABLE_INLINE = re.compile(r"#\s*rivt:\s*disable=(\S+)")
_DISABLE_NEXT = re.compile(r"#\s*rivt:\s*disable-next-line=(\S+)")
_DISABLE_FILE = re.compile(r"#\s*rivt:\s*disable-file=(\S+)")


def find_python_files(project_root: Path, config: RivtConfig) -> list[Path]:
    files: list[Path] = []
    for py_file in project_root.rglob("*.py"):
        rel_path = py_file.relative_to(project_root)

        if any(part in ALWAYS_EXCLUDE for part in rel_path.parts):
            continue

        rel_str = str(rel_path)
        if any(fnmatch(rel_str, pattern) for pattern in config.exclude):
            continue

        files.append(py_file)
    return sorted(files)


def run_checks(project_root: Path, config: RivtConfig) -> list[Violation]:
    plugin_rules = load_plugin_rules(project_root, config.plugins)
    all_rules = [*ALL_RULES, *plugin_rules]
    active_rules = [r for r in all_rules if r.id not in config.disable]

    all_violations: list[Violation] = []
    files = find_python_files(project_root, config)

    for py_file in files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = py_file.relative_to(project_root)

        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            all_violations.append(
                Violation(
                    rule_id="parse-error",
                    path=str(rel_path),
                    line=exc.lineno or 0,
                    col=(exc.offset or 1) - 1,
                    message=f"Failed to parse: {exc.msg}",
                )
            )
            continue

        source_lines = source.splitlines()
        file_disabled = _file_disabled_rules(source_lines)
        next_line_disabled = _next_line_disabled_rules(source_lines)

        for rule in active_rules:
            if rule.id in file_disabled:
                continue
            for v in rule.check(tree, rel_path, config):
                if _is_inline_suppressed(v, source_lines):
                    continue
                if (
                    v.line in next_line_disabled
                    and v.rule_id in next_line_disabled[v.line]
                ):
                    continue
                all_violations.append(v)

    all_violations.sort(key=lambda v: (v.path, v.line, v.col))
    return all_violations


def _file_disabled_rules(source_lines: list[str]) -> set[str]:
    """Collect rule IDs from ``# rivt: disable-file=...`` in the first 10 lines."""
    disabled: set[str] = set()
    for line in source_lines[:10]:
        match = _DISABLE_FILE.search(line)
        if match:
            disabled.update(match.group(1).split(","))
    return disabled


def _next_line_disabled_rules(source_lines: list[str]) -> dict[int, set[str]]:
    """Map 1-based line numbers to rule IDs suppressed via disable-next-line."""
    disabled: dict[int, set[str]] = {}
    for idx, line in enumerate(source_lines):
        match = _DISABLE_NEXT.search(line)
        if match:
            target_line = idx + 2  # 1-based line number of the NEXT line
            rule_ids = set(match.group(1).split(","))
            disabled.setdefault(target_line, set()).update(rule_ids)
    return disabled


def _is_inline_suppressed(violation: Violation, source_lines: list[str]) -> bool:
    line_idx = violation.line - 1
    if line_idx < 0 or line_idx >= len(source_lines):
        return False
    match = _DISABLE_INLINE.search(source_lines[line_idx])
    if match:
        return violation.rule_id in match.group(1).split(",")
    return False
