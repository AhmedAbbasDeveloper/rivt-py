from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from pathlib import Path

from rivt.models import RivtConfig, Violation


class Rule(ABC):
    id: str
    description: str

    @abstractmethod
    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]: ...
