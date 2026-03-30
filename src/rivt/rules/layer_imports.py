"""layer-imports: Enforce import boundaries between architectural layers."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import Layer, RivtConfig, Violation, matches_pattern
from rivt.rules.base import Rule


def _resolve_relative_import(file_path: Path, level: int, module: str | None) -> str:
    dir_path = file_path.parent
    parts = list(dir_path.parts)

    num_up = level - 1
    base_parts = parts[: len(parts) - num_up] if num_up < len(parts) else []

    base_module = ".".join(base_parts) if base_parts else ""
    if module:
        return f"{base_module}.{module}" if base_module else module
    return base_module


def _module_to_layer(module_path: str, config: RivtConfig) -> Layer | None:
    """Map a dotted module path to its layer."""
    path_str = module_path.replace(".", "/")

    best: Layer | None = None
    best_len = -1

    for layer in config.layers.values():
        for pattern in layer.paths:
            pattern_norm = pattern.replace("\\", "/")
            matched = (
                matches_pattern(path_str, pattern_norm)
                or matches_pattern(path_str + ".py", pattern_norm)
                or matches_pattern(path_str + "/__init__.py", pattern_norm)
            )
            if matched and len(pattern_norm) > best_len:
                best_len = len(pattern_norm)
                best = layer

    return best


class LayerImportsRule(Rule):
    id = "layer-imports"
    description = "Enforce import boundaries between architectural layers"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        current_layer = config.get_layer(file_path)
        if current_layer is None:
            return []

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import(
                        file_path,
                        alias.name,
                        alias.name,
                        node.lineno,
                        node.col_offset,
                        current_layer,
                        config,
                        violations,
                    )
            elif isinstance(node, ast.ImportFrom):
                module_path = self._resolve_module(file_path, node)
                if module_path is None:
                    continue

                if node.names:
                    first = node.names[0]
                    found = (
                        module_path
                        if first.name == "*"
                        else f"{module_path}.{first.name}"
                    )
                else:
                    found = module_path

                self._check_import(
                    file_path,
                    module_path,
                    found,
                    node.lineno,
                    node.col_offset,
                    current_layer,
                    config,
                    violations,
                )

        return violations

    def _resolve_module(self, file_path: Path, node: ast.ImportFrom) -> str | None:
        if node.level and node.level > 0:
            try:
                return _resolve_relative_import(file_path, node.level, node.module)
            except (ValueError, IndexError):
                return None
        return node.module

    def _check_import(
        self,
        file_path: Path,
        module_path: str,
        found: str,
        line: int,
        col: int,
        current_layer: Layer,
        config: RivtConfig,
        violations: list[Violation],
    ) -> None:
        target_layer = _module_to_layer(module_path, config)
        if target_layer is None:
            return
        if target_layer.name == current_layer.name:
            return
        if target_layer.name in current_layer.can_import:
            return

        if current_layer.can_import:
            allowed = ", ".join(current_layer.can_import)
            suggestion = f"Import from {allowed} instead."
        else:
            suggestion = (
                "This layer cannot import from other layers."
                " It should be self-contained"
                " \u2014 pass any dependencies as function arguments."
            )

        violations.append(
            Violation(
                rule_id=self.id,
                path=str(file_path),
                line=line,
                col=col,
                message=(
                    f"{current_layer.name.capitalize()} must not import from "
                    f"{target_layer.name}. {suggestion} (found: {found})"
                ),
            )
        )
