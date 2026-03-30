"""Shared utilities for FastAPI route decorator detection."""

from __future__ import annotations

import ast

ROUTE_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
)
STATUS_CODE_METHODS = frozenset({"post", "delete"})


def get_route_decorators(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[ast.Call, str]]:
    """Find all FastAPI route decorators on a function.

    Returns a list of (decorator_call_node, method) tuples.
    """
    result: list[tuple[ast.Call, str]] = []
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr not in ROUTE_METHODS:
            continue
        result.append((decorator, decorator.func.attr))
    return result


def has_keyword_arg(call_node: ast.Call, name: str) -> bool:
    """Check if a Call node has a keyword argument with the given name."""
    return any(kw.arg == name for kw in call_node.keywords if kw.arg is not None)
