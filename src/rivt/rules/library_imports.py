"""library-imports: Restrict libraries to specific architectural layers."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import Layer, RivtConfig, Violation
from rivt.rules.base import Rule


class LibraryImportsRule(Rule):
    id = "library-imports"
    description = "Restrict libraries to specific architectural layers"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        if not config.libraries:
            return []

        current_layer = config.get_layer(file_path)
        if current_layer is None:
            return []

        violations: list[Violation] = []

        for node in ast.walk(tree):
            top_level: str | None = None
            found: str | None = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    found = alias.name
                    self._check(
                        file_path,
                        top_level,
                        found,
                        node.lineno,
                        node.col_offset,
                        current_layer,
                        config,
                        violations,
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.level and node.level > 0:
                    continue
                top_level = node.module.split(".")[0]
                first = node.names[0] if node.names else None
                if first and first.name != "*":
                    found = f"{node.module}.{first.name}"
                else:
                    found = node.module
                self._check(
                    file_path,
                    top_level,
                    found,
                    node.lineno,
                    node.col_offset,
                    current_layer,
                    config,
                    violations,
                )

        return violations

    def _check(
        self,
        file_path: Path,
        top_level: str,
        found: str,
        line: int,
        col: int,
        current_layer: Layer,
        config: RivtConfig,
        violations: list[Violation],
    ) -> None:
        restriction = config.libraries.get(top_level)
        if restriction is None:
            return
        if current_layer.name in restriction.allowed_in:
            return

        allowed_str = ", ".join(restriction.allowed_in)
        msg = (
            f"{current_layer.name.capitalize()} must not import {top_level}. "
            f"Move {top_level} usage to the {allowed_str} "
            f"{'layers' if len(restriction.allowed_in) > 1 else 'layer'}. "
            f"(found: {found})"
        )

        if top_level == "fastapi" and current_layer.name == "services":
            msg = (
                "Services must not import fastapi. Raise a domain exception and "
                f"handle it in the router layer. (found: {found})"
            )

        violations.append(
            Violation(
                rule_id=self.id,
                path=str(file_path),
                line=line,
                col=col,
                message=msg,
            )
        )
