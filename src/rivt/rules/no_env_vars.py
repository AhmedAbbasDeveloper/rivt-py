"""no-env-vars: Disallow direct env var access outside config modules."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules.base import Rule


class NoEnvVarsRule(Rule):
    id = "no-env-vars"
    description = "No os.environ / os.getenv outside the config module"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        if config.is_config_module(file_path):
            return []

        violations: list[Violation] = []
        seen: set[tuple[int, int]] = set()
        msg = self._message(config)

        def add(line: int, col: int) -> None:
            if (line, col) not in seen:
                seen.add((line, col))
                violations.append(
                    Violation(
                        rule_id=self.id,
                        path=str(file_path),
                        line=line,
                        col=col,
                        message=msg,
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                func = node.func
                if (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                    and func.attr == "getenv"
                ):
                    add(node.lineno, node.col_offset)
                    continue
                if (
                    isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "os"
                    and func.value.attr == "environ"
                    and func.attr == "get"
                ):
                    add(node.lineno, node.col_offset)
                    continue

            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ):
                add(node.lineno, node.col_offset)

            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
                and node.value.attr == "environ"
            ):
                add(node.lineno, node.col_offset)

        return violations

    def _message(self, config: RivtConfig) -> str:
        if config.config_module:
            modules = ", ".join(config.config_module)
            return (
                "Do not access environment variables directly."
                f" Read from the config module instead ({modules})."
            )
        return (
            "Do not access environment variables directly."
            " Read from the config module instead."
        )
