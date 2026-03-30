"""Pytest configuration and fixtures."""

import pytest

from rivt.models import Layer, LibraryRestriction, RivtConfig


@pytest.fixture
def fastapi_config() -> RivtConfig:
    """Create a FastAPI-like RivtConfig for testing."""
    return RivtConfig(
        config_module=["app/core/config.py"],
        orm="sqlalchemy",
        http_client="httpx",
        layers={
            "routers": Layer(
                name="routers",
                paths=["app/routers"],
                can_import=["services", "schemas"],
            ),
            "services": Layer(
                name="services",
                paths=["app/services"],
                can_import=["repositories", "clients", "schemas"],
            ),
            "repositories": Layer(
                name="repositories",
                paths=["app/repositories"],
                can_import=["schemas", "models"],
            ),
            "clients": Layer(
                name="clients",
                paths=["app/clients"],
                can_import=["schemas"],
            ),
            "schemas": Layer(
                name="schemas",
                paths=["app/schemas"],
                can_import=[],
            ),
            "models": Layer(
                name="models",
                paths=["app/models"],
                can_import=[],
            ),
        },
        libraries={
            "fastapi": LibraryRestriction(name="fastapi", allowed_in=["routers"]),
            "sqlalchemy": LibraryRestriction(
                name="sqlalchemy",
                allowed_in=["repositories", "models"],
            ),
            "httpx": LibraryRestriction(name="httpx", allowed_in=["clients"]),
        },
    )
