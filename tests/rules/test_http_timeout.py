"""Tests for http-timeout rule."""

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.http_timeout import HttpTimeoutRule

rule = HttpTimeoutRule()


def _check(source: str, config: RivtConfig) -> int:
    tree = ast.parse(source)
    return len(rule.check(tree, Path("app/clients/stripe.py"), config))


class TestHttpTimeout:
    def test_missing_timeout_get(self, fastapi_config: RivtConfig) -> None:
        source = 'response = httpx.get("https://api.example.com")'
        assert _check(source, fastapi_config) == 1

    def test_has_timeout(self, fastapi_config: RivtConfig) -> None:
        source = 'response = httpx.get("https://api.example.com", timeout=10)'
        assert _check(source, fastapi_config) == 0

    def test_client_constructor(self, fastapi_config: RivtConfig) -> None:
        source = "client = httpx.Client()"
        assert _check(source, fastapi_config) == 1

    def test_client_with_timeout(self, fastapi_config: RivtConfig) -> None:
        source = "client = httpx.Client(timeout=30)"
        assert _check(source, fastapi_config) == 0

    def test_no_http_client_configured(self) -> None:
        config = RivtConfig()
        source = 'response = httpx.get("https://api.example.com")'
        assert _check(source, config) == 0

    def test_requests_library(self) -> None:
        config = RivtConfig(http_client="requests")
        source = 'response = requests.get("https://api.example.com")'
        assert _check(source, config) == 1

    def test_unrelated_method_ignored(self, fastapi_config: RivtConfig) -> None:
        source = "httpx.some_other_method()"
        assert _check(source, fastapi_config) == 0

    def test_async_client_missing_timeout(self, fastapi_config: RivtConfig) -> None:
        source = "client = httpx.AsyncClient()"
        assert _check(source, fastapi_config) == 1
