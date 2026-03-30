"""response-model: FastAPI route handlers must declare a response type."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules.base import Rule

from .route_utils import get_route_decorators, has_keyword_arg


class ResponseModelRule(Rule):
    id = "response-model"
    description = "Route handlers must declare a response type"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        violations: list[Violation] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator, _method in get_route_decorators(node):
                    if has_keyword_arg(decorator, "response_model"):
                        continue
                    if node.returns is not None:
                        continue
                    decorator_src = ast.unparse(decorator.func)
                    violations.append(
                        Violation(
                            rule_id=self.id,
                            path=str(file_path),
                            line=node.lineno,
                            col=node.col_offset,
                            message=(
                                f"Add response_model to @{decorator_src}()"
                                " or a return type annotation."
                            ),
                        )
                    )
        return violations
