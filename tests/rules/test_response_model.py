"""Tests for response-model rule."""

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.response_model import ResponseModelRule

rule = ResponseModelRule()


def _check(source: str, config: RivtConfig) -> int:
    tree = ast.parse(source)
    return len(rule.check(tree, Path("app/routers/users.py"), config))


class TestResponseModel:
    def test_missing_both(self, fastapi_config: RivtConfig) -> None:
        source = '@router.get("/users")\ndef get_users(): ...'
        assert _check(source, fastapi_config) == 1

    def test_has_response_model(self, fastapi_config: RivtConfig) -> None:
        source = (
            '@router.get("/users", response_model=list[User])\ndef get_users(): ...'
        )
        assert _check(source, fastapi_config) == 0

    def test_has_return_annotation(self, fastapi_config: RivtConfig) -> None:
        source = '@router.get("/users")\ndef get_users() -> list[User]: ...'
        assert _check(source, fastapi_config) == 0

    def test_non_route_decorator_ignored(self, fastapi_config: RivtConfig) -> None:
        source = "@auth_required\ndef get_users(): ..."
        assert _check(source, fastapi_config) == 0

    def test_async_handler(self, fastapi_config: RivtConfig) -> None:
        source = '@router.get("/users")\nasync def get_users(): ...'
        assert _check(source, fastapi_config) == 1

    def test_non_route_method_ignored(self, fastapi_config: RivtConfig) -> None:
        source = "def helper(): ..."
        assert _check(source, fastapi_config) == 0
