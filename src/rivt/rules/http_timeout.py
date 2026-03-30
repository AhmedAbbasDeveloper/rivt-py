"""http-timeout: Require timeout parameter on HTTP client calls."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules.base import Rule

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
HTTP_CLIENT_CONSTRUCTORS = {"Client", "AsyncClient", "Session"}


class HttpTimeoutRule(Rule):
    id = "http-timeout"
    description = "HTTP calls must specify a timeout"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        http_client = config.http_client
        if not http_client:
            return []

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if not isinstance(node.func.value, ast.Name):
                continue
            if node.func.value.id != http_client:
                continue

            attr = node.func.attr
            if attr not in HTTP_METHODS and attr not in HTTP_CLIENT_CONSTRUCTORS:
                continue

            if not any(kw.arg == "timeout" for kw in node.keywords):
                violations.append(
                    Violation(
                        rule_id=self.id,
                        path=str(file_path),
                        line=node.lineno,
                        col=node.col_offset,
                        message=f"Add timeout parameter to {http_client}.{attr}()"
                        " (e.g. timeout=10).",
                    )
                )

        return violations
