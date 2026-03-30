"""Tests for library-imports rule."""

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.library_imports import LibraryImportsRule

rule = LibraryImportsRule()


def _check(source: str, file_path: str, config: RivtConfig) -> list[str]:
    tree = ast.parse(source)
    return [v.message for v in rule.check(tree, Path(file_path), config)]


class TestLibraryRestrictions:
    def test_allowed_library(self, fastapi_config: RivtConfig) -> None:
        source = "from sqlalchemy import Column"
        assert _check(source, "app/repositories/user.py", fastapi_config) == []

    def test_orm_in_wrong_layer(self, fastapi_config: RivtConfig) -> None:
        source = "from sqlalchemy import Column"
        violations = _check(source, "app/services/user.py", fastapi_config)
        assert len(violations) == 1
        assert "sqlalchemy" in violations[0].lower()
        assert "move" in violations[0].lower()

    def test_fastapi_in_services(self, fastapi_config: RivtConfig) -> None:
        source = "from fastapi import HTTPException"
        violations = _check(source, "app/services/user.py", fastapi_config)
        assert len(violations) == 1
        assert "domain exception" in violations[0].lower()

    def test_fastapi_in_routers_allowed(self, fastapi_config: RivtConfig) -> None:
        source = "from fastapi import APIRouter"
        assert _check(source, "app/routers/users.py", fastapi_config) == []

    def test_http_client_in_wrong_layer(self, fastapi_config: RivtConfig) -> None:
        source = "import httpx"
        violations = _check(source, "app/services/email.py", fastapi_config)
        assert len(violations) == 1
        assert "httpx" in violations[0].lower()

    def test_http_client_in_clients_allowed(self, fastapi_config: RivtConfig) -> None:
        source = "import httpx"
        assert _check(source, "app/clients/stripe.py", fastapi_config) == []

    def test_no_libraries_configured(self) -> None:
        config = RivtConfig()
        source = "from sqlalchemy import Column"
        assert _check(source, "app/services/user.py", config) == []

    def test_file_outside_layer_ignored(self, fastapi_config: RivtConfig) -> None:
        source = "from sqlalchemy import Column"
        assert _check(source, "scripts/migrate.py", fastapi_config) == []

    def test_relative_import_skipped(self, fastapi_config: RivtConfig) -> None:
        source = "from . import models"
        assert _check(source, "app/services/user.py", fastapi_config) == []
