from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path


class RivtError(Exception):
    """Raised for rivt configuration and plugin errors."""


@dataclass
class Violation:
    rule_id: str
    path: str
    line: int
    col: int
    message: str


@dataclass
class Layer:
    name: str
    paths: list[str]
    can_import: list[str] = field(default_factory=list[str])


@dataclass
class LibraryRestriction:
    name: str
    allowed_in: list[str]


def matches_pattern(file_path: str, pattern: str) -> bool:
    """Match a file path against a layer pattern.

    Three modes:
      - Glob (contains *, ?, [): fnmatch against the path and path.py
      - Exact file (ends with .py): exact string match
      - Directory prefix: file must be under that directory
    """
    if any(c in pattern for c in ("*", "?", "[")):
        return fnmatch(file_path, pattern) or fnmatch(file_path + ".py", pattern)
    if pattern.endswith(".py"):
        return file_path == pattern
    return file_path.startswith(pattern + "/")


@dataclass
class RivtConfig:
    config_module: list[str] = field(default_factory=list[str])
    http_client: str = ""
    orm: str = ""
    exclude: list[str] = field(default_factory=list[str])
    disable: list[str] = field(default_factory=list[str])
    plugins: list[str] = field(default_factory=list[str])
    layers: dict[str, Layer] = field(default_factory=dict[str, Layer])
    libraries: dict[str, LibraryRestriction] = field(
        default_factory=dict[str, LibraryRestriction]
    )

    def get_layer(self, file_path: Path | str) -> Layer | None:
        """Match a file path against configured layer patterns.

        Supports directory prefixes, exact .py paths, and glob patterns.
        When multiple layers match, the longest pattern wins.
        """
        path_str = str(file_path).replace("\\", "/")
        best: Layer | None = None
        best_len = -1

        for layer in self.layers.values():
            for pattern in layer.paths:
                pattern_norm = pattern.replace("\\", "/")
                if (
                    matches_pattern(path_str, pattern_norm)
                    and len(pattern_norm) > best_len
                ):
                    best_len = len(pattern_norm)
                    best = layer

        return best

    def is_config_module(self, file_path: Path | str) -> bool:
        """Check whether a file is one of the configured config modules."""
        path_str = str(file_path).replace("\\", "/")
        return any(
            matches_pattern(path_str, m.replace("\\", "/")) for m in self.config_module
        )
