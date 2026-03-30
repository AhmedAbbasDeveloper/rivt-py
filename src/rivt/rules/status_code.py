"""status-code: POST and DELETE handlers must declare explicit status_code."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules.base import Rule

from .route_utils import STATUS_CODE_METHODS, get_route_decorators, has_keyword_arg


class StatusCodeRule(Rule):
    id = "status-code"
    description = "POST/DELETE handlers must declare status_code"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        violations: list[Violation] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator, method in get_route_decorators(node):
                    if method not in STATUS_CODE_METHODS:
                        continue
                    if has_keyword_arg(decorator, "status_code"):
                        continue
                    decorator_src = ast.unparse(decorator.func)
                    example = (
                        "status_code=204" if method == "delete" else "status_code=201"
                    )
                    msg = f"Add status_code to @{decorator_src}() (e.g. {example})."
                    violations.append(
                        Violation(
                            rule_id=self.id,
                            path=str(file_path),
                            line=node.lineno,
                            col=node.col_offset,
                            message=msg,
                        )
                    )
        return violations
