"""Tests for layer-imports rule."""

import ast
from pathlib import Path

from rivt.models import Layer, RivtConfig
from rivt.rules.layer_imports import LayerImportsRule

rule = LayerImportsRule()


def _check(source: str, file_path: str, config: RivtConfig) -> list[str]:
    tree = ast.parse(source)
    return [v.message for v in rule.check(tree, Path(file_path), config)]


class TestLayerToLayer:
    def test_allowed_import(self, fastapi_config: RivtConfig) -> None:
        source = "from app.services.user import UserService"
        assert _check(source, "app/routers/users.py", fastapi_config) == []

    def test_forbidden_import(self, fastapi_config: RivtConfig) -> None:
        source = "from app.repositories.user import get_user"
        violations = _check(source, "app/routers/users.py", fastapi_config)
        assert len(violations) == 1
        assert "Routers must not import from repositories" in violations[0]

    def test_self_layer_allowed(self, fastapi_config: RivtConfig) -> None:
        source = "from app.services.email import send_email"
        assert _check(source, "app/services/order.py", fastapi_config) == []

    def test_file_outside_layer_ignored(self, fastapi_config: RivtConfig) -> None:
        source = "from app.routers.user import router"
        assert _check(source, "scripts/migrate.py", fastapi_config) == []

    def test_relative_import_violation(self, fastapi_config: RivtConfig) -> None:
        source = "from ..repositories.user import get_user"
        violations = _check(source, "app/routers/users.py", fastapi_config)
        assert len(violations) == 1

    def test_star_import_violation(self, fastapi_config: RivtConfig) -> None:
        source = "from app.repositories import *"
        violations = _check(source, "app/routers/users.py", fastapi_config)
        assert len(violations) == 1


class TestGlobPaths:
    def test_glob_pattern_matching(self) -> None:
        config = RivtConfig(
            layers={
                "routers": Layer(
                    name="routers",
                    paths=["src/**/router.py"],
                    can_import=["services"],
                ),
                "services": Layer(
                    name="services",
                    paths=["src/**/service.py"],
                    can_import=[],
                ),
            },
        )
        source = "from src.orders.service import OrderService"
        violations = _check(source, "src/users/router.py", config)
        assert violations == []

    def test_glob_pattern_violation(self) -> None:
        config = RivtConfig(
            layers={
                "routers": Layer(
                    name="routers",
                    paths=["src/**/router.py"],
                    can_import=["services"],
                ),
                "repositories": Layer(
                    name="repositories",
                    paths=["src/**/repository.py"],
                    can_import=[],
                ),
            },
        )
        source = "from src.users.repository import UserRepo"
        violations = _check(source, "src/users/router.py", config)
        assert len(violations) == 1
        assert "Routers must not import from repositories" in violations[0]


class TestSingleFilePath:
    def test_single_file_model(self, fastapi_config: RivtConfig) -> None:
        fastapi_config.layers["models"] = Layer(
            name="models",
            paths=["src/models.py"],
            can_import=[],
        )
        source = "from src.models import User"
        violations = _check(source, "app/routers/users.py", fastapi_config)
        assert len(violations) == 1

    def test_single_file_as_source(self) -> None:
        config = RivtConfig(
            layers={
                "models": Layer(name="models", paths=["src/models.py"], can_import=[]),
                "services": Layer(
                    name="services", paths=["src/services"], can_import=[]
                ),
            },
        )
        source = "from src.services.user import UserService"
        violations = _check(source, "src/models.py", config)
        assert len(violations) == 1
