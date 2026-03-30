"""Tests for status-code rule."""

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.status_code import StatusCodeRule

rule = StatusCodeRule()


def _check(source: str, config: RivtConfig) -> int:
    tree = ast.parse(source)
    return len(rule.check(tree, Path("app/routers/users.py"), config))


class TestStatusCode:
    def test_post_missing(self, fastapi_config: RivtConfig) -> None:
        source = '@router.post("/users")\ndef create_user(): ...'
        assert _check(source, fastapi_config) == 1

    def test_post_present(self, fastapi_config: RivtConfig) -> None:
        source = '@router.post("/users", status_code=201)\ndef create_user(): ...'
        assert _check(source, fastapi_config) == 0

    def test_delete_missing(self, fastapi_config: RivtConfig) -> None:
        source = '@router.delete("/users/{id}")\ndef delete_user(): ...'
        assert _check(source, fastapi_config) == 1

    def test_get_not_checked(self, fastapi_config: RivtConfig) -> None:
        source = '@router.get("/users")\ndef get_users(): ...'
        assert _check(source, fastapi_config) == 0

    def test_put_not_checked(self, fastapi_config: RivtConfig) -> None:
        source = '@router.put("/users/{id}")\ndef update_user(): ...'
        assert _check(source, fastapi_config) == 0

    def test_patch_not_checked(self, fastapi_config: RivtConfig) -> None:
        source = '@router.patch("/users/{id}")\ndef update_user(): ...'
        assert _check(source, fastapi_config) == 0
