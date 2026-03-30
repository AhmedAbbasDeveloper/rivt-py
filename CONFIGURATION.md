# Configuration

All rivt configuration lives in `pyproject.toml` under `[tool.rivt]`.

## Layers

Each layer defines two things: `paths` (where the files live) and `can_import` (which other layers it can import from):

```toml
[tool.rivt.layers.routers]
paths = ["app/routers"]
can_import = ["services", "schemas"]

[tool.rivt.layers.services]
paths = ["app/services"]
can_import = ["repositories", "clients", "schemas"]

[tool.rivt.layers.repositories]
paths = ["app/repositories"]
can_import = ["schemas", "models"]
```

The config file is the source of truth. rivt enforces exactly what's written — a layer with `can_import = []` cannot import from any other layer, and a layer without `can_import` is treated the same way.

`rivt init` generates a complete config with conventional import relationships for standard FastAPI layer names. You can adjust it from there.

### Path types

Paths can be directories, exact files, or glob patterns:

```toml
# Directory — matches all .py files under app/routers/
paths = ["app/routers"]

# Exact file — matches only this file
paths = ["app/models.py"]

# Glob — matches src/users/router.py, src/orders/router.py, etc.
paths = ["src/**/router.py"]
```

Glob patterns are useful for feature-based / vertical slicing layouts:

```toml
[tool.rivt.layers.routers]
paths = ["src/**/router.py"]
can_import = ["services", "schemas"]

[tool.rivt.layers.services]
paths = ["src/**/service.py"]
can_import = ["repositories", "clients", "schemas"]

[tool.rivt.layers.repositories]
paths = ["src/**/repository.py"]
can_import = ["schemas", "models"]
```

### Layer matching

When a file matches multiple layers, the longest pattern wins. Files that don't match any layer are not checked by `layer-imports` or `library-imports`.

## Library restrictions

Control which layers can import specific libraries:

```toml
[tool.rivt.libraries.sqlalchemy]
allowed_in = ["repositories", "models"]

[tool.rivt.libraries.fastapi]
allowed_in = ["routers"]
```

rivt auto-generates some library restrictions based on your settings:

- `fastapi` is always restricted to `routers`
- `orm = "sqlalchemy"` restricts `sqlalchemy` to `repositories` and `models`
- `http_client = "httpx"` restricts `httpx` to `clients`

Use `[tool.rivt.libraries.*]` to override any of these or add your own.

## Settings reference

```toml
[tool.rivt]
orm = "sqlalchemy"                                # restricts ORM to repositories, models
http_client = "httpx"                             # restricts HTTP client to clients
config_module = "app/core/config.py"              # where env vars are read
exclude = ["tests/**", "migrations/**"]           # glob patterns to skip
disable = ["status-code"]                         # rule IDs to turn off
plugins = ["my_rivt_rules"]                       # plugin modules to load
```

### config_module

Accepts a string or a list. Supports glob patterns:

```toml
config_module = "app/core/config.py"
config_module = ["app/core/config.py", "app/core/settings.py"]
config_module = ["app/core/*.py"]
```

Files matching `config_module` are exempt from the `no-env-vars` rule.

### exclude

Glob patterns for files and directories to skip entirely:

```toml
exclude = ["tests/**", "migrations/**", "scripts/**"]
```

rivt always excludes `.venv`, `venv`, `.git`, `node_modules`, `__pycache__`, `.tox`, `.eggs`, `.rivt`, `build`, and `dist`.

### disable

Rule IDs to turn off globally:

```toml
disable = ["status-code", "response-model"]
```

## Suppression

For granular control, suppress rules inline instead of disabling them globally.

### Inline — suppress on this line

```python
from app.repositories.user import UserRepo  # rivt: disable=layer-imports
```

### Next-line — suppress on the following line

```python
# rivt: disable-next-line=library-imports
from sqlalchemy import text
```

### File-level — suppress for the entire file

Must appear in the first 10 lines:

```python
# rivt: disable-file=no-env-vars
```

### Multiple rules

Comma-separate rule IDs in any suppression comment:

```python
# rivt: disable=layer-imports,library-imports
```

## Custom rules

### Scaffold a rule

```bash
rivt new-rule handle-db-errors
# Created .rivt/rules/handle_db_errors.py
```

This generates a rule file with boilerplate. Fill in the `check` method — or point your AI agent at the file and tell it what to enforce. The API is intentionally simple: you get an AST, a file path, and the config. Return violations.

### Discovery

rivt auto-discovers `Rule` subclasses from `.rivt/rules/`. No config changes needed. Drop a file, run `rivt check`.

```
my-project/
  .rivt/
    rules/
      handle_db_errors.py
      async_service_methods.py
  src/
    ...
```

Files starting with `_` are ignored. Custom rules support the same `disable` and inline suppression as built-in rules.

### Writing a rule

A rule is a class that inherits from `Rule` and implements `check`:

```python
# .rivt/rules/handle_db_errors.py
import ast
from pathlib import Path

from rivt import Rule, RivtConfig, Violation


class HandleDbErrorsRule(Rule):
    id = "handle-db-errors"
    description = "Require @handle_db_errors on repository methods"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig,
    ) -> list[Violation]:
        layer = config.get_layer(file_path)
        if not layer or layer.name != "repositories":
            return []

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name.startswith("_"):
                    continue
                has_it = any(
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Name)
                    and d.func.id == "handle_db_errors"
                    for d in item.decorator_list
                )
                if not has_it:
                    violations.append(Violation(
                        rule_id=self.id,
                        path=str(file_path),
                        line=item.lineno,
                        col=item.col_offset,
                        message=f"Public method '{item.name}' must be decorated with @handle_db_errors.",
                    ))
        return violations
```

Key APIs available in `check`:
- `config.get_layer(file_path)` — returns the `Layer` the file belongs to (or `None`)
- `config.is_config_module(file_path)` — whether the file is a config module
- `ast.walk(tree)` — traverse the AST
- Return a list of `Violation(rule_id, path, line, col, message)`

### Sharing rules across repos

For rules you want in every repo, publish a Python package with entry points:

```toml
# In your plugin package's pyproject.toml
[project.entry-points."rivt.plugins"]
my_org = "my_rivt_rules:get_rules"
```

```python
# my_rivt_rules/__init__.py
def get_rules():
    return [HandleDbErrorsRule(), AsyncHandlersRule()]
```

Install the package and rivt picks up the rules automatically. You can also list plugins explicitly:

```toml
[tool.rivt]
plugins = ["my_rivt_rules"]
```
