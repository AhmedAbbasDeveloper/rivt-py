from __future__ import annotations

from rivt.rules.base import Rule

from .http_timeout import HttpTimeoutRule
from .layer_imports import LayerImportsRule
from .library_imports import LibraryImportsRule
from .no_env_vars import NoEnvVarsRule
from .response_model import ResponseModelRule
from .status_code import StatusCodeRule

ALL_RULES: list[Rule] = [
    LayerImportsRule(),
    LibraryImportsRule(),
    NoEnvVarsRule(),
    ResponseModelRule(),
    StatusCodeRule(),
    HttpTimeoutRule(),
]

BUILTIN_IDS: frozenset[str] = frozenset(r.id for r in ALL_RULES)
