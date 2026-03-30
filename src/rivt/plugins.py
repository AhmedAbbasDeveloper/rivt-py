"""Plugin discovery and loading for custom rules."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import inspect
from pathlib import Path
from typing import cast

from rivt.models import RivtError
from rivt.rules.base import Rule

LOCAL_RULES_DIR = ".rivt/rules"


def load_plugin_rules(project_root: Path, plugins: list[str]) -> list[Rule]:
    """Load custom rules from all discovery mechanisms.

    Discovery order:
        1. Local files in .rivt/rules/
        2. Entry points registered under "rivt.plugins"
        3. Modules listed in [tool.rivt] plugins config
    """
    rules: list[Rule] = []
    seen_modules: set[str] = set()

    rules.extend(_load_local_rules(project_root))
    rules.extend(_load_entry_point_rules(seen_modules))
    rules.extend(_load_config_plugin_rules(plugins, seen_modules))

    _validate_plugin_rules(rules)

    return rules


def _load_local_rules(project_root: Path) -> list[Rule]:
    rules_dir = project_root / LOCAL_RULES_DIR
    if not rules_dir.is_dir():
        return []

    rules: list[Rule] = []
    for py_file in sorted(rules_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        rules.extend(_load_rules_from_file(py_file))
    return rules


def _load_rules_from_file(py_file: Path) -> list[Rule]:
    module_name = f"rivt_custom_rules.{py_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if spec is None or spec.loader is None:
        raise RivtError(f"Failed to load {py_file}: could not create module spec.")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RivtError(f"Failed to load {py_file}: {exc}") from exc

    rules: list[Rule] = []
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Rule) and obj is not Rule and not inspect.isabstract(obj):
            rules.append(obj())
    return rules


def _load_entry_point_rules(seen_modules: set[str]) -> list[Rule]:
    rules: list[Rule] = []
    plugin_eps = importlib.metadata.entry_points(group="rivt.plugins")

    for ep in plugin_eps:
        module_name = ep.value.rsplit(":", 1)[0]
        seen_modules.add(module_name)
        rules.extend(_load_rules_from_entry_point(ep))

    return rules


def _load_rules_from_entry_point(ep: importlib.metadata.EntryPoint) -> list[Rule]:
    try:
        get_rules = ep.load()
    except Exception as exc:
        raise RivtError(f"Failed to load plugin '{ep.name}': {exc}") from exc

    if not callable(get_rules):
        raise RivtError(
            f"Plugin '{ep.name}' entry point does not resolve to a callable."
        )

    try:
        plugin_rules = get_rules()
    except Exception as exc:
        raise RivtError(f"Plugin '{ep.name}' get_rules() failed: {exc}") from exc

    if not isinstance(plugin_rules, list):
        raise RivtError(f"Plugin '{ep.name}' get_rules() must return a list of Rules.")

    return cast(list[Rule], plugin_rules)


def _load_config_plugin_rules(plugins: list[str], seen_modules: set[str]) -> list[Rule]:
    rules: list[Rule] = []
    for module_path in plugins:
        base_module = (
            module_path.rsplit(":", 1)[0] if ":" in module_path else module_path
        )
        if base_module in seen_modules:
            continue
        seen_modules.add(base_module)
        rules.extend(_load_rules_from_module(module_path))
    return rules


def _load_rules_from_module(module_path: str) -> list[Rule]:
    if ":" in module_path:
        mod_name, func_name = module_path.rsplit(":", 1)
    else:
        mod_name, func_name = module_path, "get_rules"

    try:
        module = importlib.import_module(mod_name)
    except Exception as exc:
        raise RivtError(f"Failed to import plugin module '{mod_name}': {exc}") from exc

    get_rules = getattr(module, func_name, None)
    if get_rules is None:
        raise RivtError(f"Plugin module '{mod_name}' has no '{func_name}()' function.")

    try:
        plugin_rules = get_rules()
    except Exception as exc:
        raise RivtError(f"Plugin '{mod_name}' {func_name}() failed: {exc}") from exc

    if not isinstance(plugin_rules, list):
        raise RivtError(
            f"Plugin '{mod_name}' {func_name}() must return a list of Rules."
        )

    return cast(list[Rule], plugin_rules)


def _validate_plugin_rules(rules: list[Rule]) -> None:
    """Ensure no custom rule collides with a built-in ID or another custom rule."""
    from rivt.rules import BUILTIN_IDS

    seen: dict[str, str] = {}
    for rule in rules:
        if rule.id in BUILTIN_IDS:
            raise RivtError(
                f"Custom rule '{rule.description}' uses reserved built-in ID "
                f"'{rule.id}'. Choose a different ID."
            )

        if rule.id in seen:
            raise RivtError(
                f"Duplicate rule ID '{rule.id}' — "
                f"found in both '{seen[rule.id]}' and '{rule.description}'."
            )
        seen[rule.id] = rule.description
