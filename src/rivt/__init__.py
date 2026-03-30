"""rivt — architectural enforcement for Python codebases."""

from importlib.metadata import version

from rivt.models import Layer, LibraryRestriction, RivtConfig, RivtError, Violation
from rivt.rules.base import Rule

__version__ = version("rivt")

__all__ = [
    "Layer",
    "LibraryRestriction",
    "RivtConfig",
    "RivtError",
    "Rule",
    "Violation",
    "__version__",
]
