from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, NoReturn

from rivt.models import Layer, LibraryRestriction, RivtConfig, RivtError

DEFAULT_CAN_IMPORT: dict[str, list[str]] = {
    "routers": ["services", "schemas"],
    "services": ["repositories", "clients", "schemas"],
    "repositories": ["schemas", "models"],
    "clients": ["schemas"],
    "schemas": [],
    "models": [],
}

DEFAULT_LIBRARY_RESTRICTIONS: dict[str, list[str]] = {
    "fastapi": ["routers"],
}


def find_project_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / "pyproject.toml").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(project_root: Path) -> RivtConfig:
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.is_file():
        _exit("No pyproject.toml found. Run 'rivt init' to create one.")

    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    maybe_config: dict[str, Any] | None = pyproject.get("tool", {}).get("rivt")
    if maybe_config is None:
        _exit(
            "No [tool.rivt] section in pyproject.toml. Run 'rivt init' to create one."
        )
    tool_config: dict[str, Any] = maybe_config

    orm: str = tool_config.get("orm", "")
    http_client: str = tool_config.get("http_client", "")
    exclude: list[str] = tool_config.get("exclude", [])
    disable: list[str] = tool_config.get("disable", [])
    plugins: list[str] = tool_config.get("plugins", [])

    raw_config_module: str | list[str] = tool_config.get("config_module", [])
    if isinstance(raw_config_module, str):
        config_module = [raw_config_module]
    else:
        config_module = list(raw_config_module)

    layers = _build_layers(tool_config)
    libraries = _build_libraries(tool_config, orm, http_client)

    return RivtConfig(
        config_module=config_module,
        http_client=http_client,
        orm=orm,
        exclude=exclude,
        disable=disable,
        plugins=plugins,
        layers=layers,
        libraries=libraries,
    )


def _build_layers(tool_config: dict[str, Any]) -> dict[str, Layer]:
    """Build the layer map from user config.

    ``can_import`` is read directly from the config.  If omitted, it
    defaults to empty (no imports allowed).  ``rivt init`` generates
    the conventional defaults explicitly so they are always visible.
    """
    layers: dict[str, Layer] = {}
    user_layers: dict[str, Any] = tool_config.get("layers", {})

    for name in sorted(user_layers):
        user_def: dict[str, Any] = user_layers[name]

        paths: str | list[str] | None = user_def.get("paths")
        if paths is None:
            continue
        if isinstance(paths, str):
            paths = [paths]

        can_import: str | list[str] = user_def.get("can_import", [])
        if isinstance(can_import, str):
            can_import = [can_import]

        layers[name] = Layer(name=name, paths=list(paths), can_import=list(can_import))

    return layers


def _build_libraries(
    tool_config: dict[str, Any],
    orm: str,
    http_client: str,
) -> dict[str, LibraryRestriction]:
    """Build library restrictions from defaults + orm/http_client + user overrides."""
    libraries: dict[str, LibraryRestriction] = {}

    for lib_name, allowed_in in DEFAULT_LIBRARY_RESTRICTIONS.items():
        libraries[lib_name] = LibraryRestriction(
            name=lib_name, allowed_in=list(allowed_in)
        )

    if orm:
        libraries[orm] = LibraryRestriction(
            name=orm, allowed_in=["repositories", "models"]
        )
    if http_client:
        libraries[http_client] = LibraryRestriction(
            name=http_client, allowed_in=["clients"]
        )

    user_libraries: dict[str, Any] = tool_config.get("libraries", {})
    for lib_name, lib_def in user_libraries.items():
        allowed_in: str | list[str] = lib_def.get("allowed_in", [])
        if isinstance(allowed_in, str):
            allowed_in = [allowed_in]
        libraries[lib_name] = LibraryRestriction(
            name=lib_name, allowed_in=list(allowed_in)
        )

    return libraries


def _exit(message: str) -> NoReturn:
    raise RivtError(message)
