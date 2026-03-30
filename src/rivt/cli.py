from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rivt.config import DEFAULT_CAN_IMPORT, find_project_root, load_config
from rivt.models import RivtError
from rivt.plugins import LOCAL_RULES_DIR
from rivt.reporter import format_violations
from rivt.runner import run_checks

COMMON_LAYER_DIRS: dict[str, list[str]] = {
    "routers": [
        "routers",
        "routes",
        "api/routers",
        "api/routes",
        "endpoints",
        "api/endpoints",
        "views",
        "api/views",
        "api",
    ],
    "services": ["services", "service", "use_cases", "usecases"],
    "repositories": [
        "repositories",
        "repository",
        "repos",
        "repo",
        "db",
        "dal",
        "crud",
        "database",
    ],
    "clients": [
        "clients",
        "client",
        "external",
        "integrations",
        "adapters",
        "gateway",
        "gateways",
    ],
    "schemas": ["schemas", "schema", "dtos", "dto"],
    "models": ["models", "model", "entities"],
}

FEATURE_FILE_NAMES: dict[str, list[str]] = {
    "routers": ["router.py", "routes.py", "endpoints.py", "views.py"],
    "services": ["service.py", "services.py"],
    "repositories": ["repository.py", "repo.py", "crud.py"],
}

CONFIG_CANDIDATES = [
    "core/config.py",
    "core/settings.py",
    "config.py",
    "settings.py",
    "config/settings.py",
    "config/config.py",
]

PREFIXES = ["src", "app", ""]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rivt",
        description="Architectural enforcement for Python codebases.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("check", help="Check codebase for violations.")
    subparsers.add_parser("init", help="Initialize rivt configuration.")

    new_rule_parser = subparsers.add_parser(
        "new-rule", help="Scaffold a new custom rule."
    )
    new_rule_parser.add_argument(
        "name", help="Rule name in kebab-case (e.g. handle-db-errors)."
    )

    args = parser.parse_args()

    if args.command == "check":
        _run_check()
    elif args.command == "init":
        _run_init()
    elif args.command == "new-rule":
        _run_new_rule(args.name)
    else:
        parser.print_help()
        sys.exit(2)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def _run_check() -> None:
    project_root = find_project_root()
    if project_root is None:
        print("Error: Could not find pyproject.toml.", file=sys.stderr)
        sys.exit(2)

    try:
        config = load_config(project_root)
        violations = run_checks(project_root, config)
    except RivtError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if violations:
        print(format_violations(violations))
        sys.exit(1)
    else:
        print("No violations found.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def _run_init() -> None:
    pyproject_path = Path.cwd() / "pyproject.toml"

    if pyproject_path.is_file():
        content = pyproject_path.read_text(encoding="utf-8")
        if "[tool.rivt]" in content:
            print("rivt is already configured in pyproject.toml.", file=sys.stderr)
            sys.exit(1)

    print("\nScanning project structure...\n")

    detected_layers = _detect_layers()
    config_module = _detect_config_module()

    if detected_layers:
        print("Detected layers:")
        for name, path in detected_layers.items():
            print(f"  {name}: {path}")
        if config_module:
            print(f"  config module: {config_module}")
        print()

        confirm = _ask("Use detected layout? [Y/n] ", default="y")
        if confirm.lower() not in ("y", "yes", ""):
            detected_layers = _manual_layer_config()
            config_module = _ask("Config module path (Enter to skip): ")
    else:
        print("No layers detected.\n")
        detected_layers = _manual_layer_config()
        if not config_module:
            config_module = _ask("Config module path (Enter to skip): ")

    orm = _prompt_choice("ORM", ["SQLAlchemy", "SQLModel", "None"])
    orm_value = {"1": "sqlalchemy", "2": "sqlmodel"}.get(orm, "")

    http = _prompt_choice("HTTP client", ["httpx", "requests", "None"])
    http_value = {"1": "httpx", "2": "requests"}.get(http, "")

    config_text = _build_config_text(
        detected_layers, config_module, orm_value, http_value
    )

    if pyproject_path.is_file():
        existing = pyproject_path.read_text(encoding="utf-8")
        with pyproject_path.open("a", encoding="utf-8") as f:
            if not existing.endswith("\n"):
                f.write("\n")
            f.write("\n")
            f.write(config_text)
    else:
        pyproject_path.write_text(config_text, encoding="utf-8")

    print(f"\nCreated rivt config in {pyproject_path}.")
    print("Run: rivt check")


def _detect_layers() -> dict[str, str]:
    """Detect layer directories and files in the project.

    Tries layer-based detection first (conventional directory names),
    then falls back to feature-based detection (e.g. src/**/router.py).
    """
    cwd = Path.cwd()
    layers: dict[str, str] = {}

    for layer_name, candidates in COMMON_LAYER_DIRS.items():
        path = _find_layer_dir(cwd, candidates)
        if path:
            layers[layer_name] = path

    for layer_name in ("models", "schemas"):
        if layer_name not in layers:
            path = _find_single_file(cwd, layer_name)
            if path:
                layers[layer_name] = path

    if not layers:
        layers = _detect_feature_layout(cwd)

    return layers


def _find_layer_dir(cwd: Path, candidates: list[str]) -> str:
    for prefix in PREFIXES:
        for candidate in candidates:
            check = cwd / prefix / candidate if prefix else cwd / candidate
            if check.is_dir():
                return f"{prefix}/{candidate}" if prefix else candidate
    return ""


def _find_single_file(cwd: Path, name: str) -> str:
    for prefix in PREFIXES:
        check = cwd / prefix / f"{name}.py" if prefix else cwd / f"{name}.py"
        if check.is_file():
            return f"{prefix}/{name}.py" if prefix else f"{name}.py"
    return ""


def _detect_feature_layout(cwd: Path) -> dict[str, str]:
    """Detect feature-based layout (e.g. src/users/router.py, src/orders/router.py)."""
    layers: dict[str, str] = {}

    for prefix in ("src", "app"):
        base = cwd / prefix
        if not base.is_dir():
            continue

        for layer_name, filenames in FEATURE_FILE_NAMES.items():
            for filename in filenames:
                matches = list(base.rglob(filename))
                if len(matches) >= 2:
                    layers[layer_name] = f"{prefix}/**/{filename}"
                    break

        if layers:
            break

    return layers


def _detect_config_module() -> str:
    cwd = Path.cwd()
    for prefix in PREFIXES:
        for candidate in CONFIG_CANDIDATES:
            check = cwd / prefix / candidate if prefix else cwd / candidate
            if check.is_file():
                return f"{prefix}/{candidate}" if prefix else candidate
    return ""


def _manual_layer_config() -> dict[str, str]:
    """Fall back to manual layer path entry."""
    print("Enter paths for each layer (Enter to skip):\n")
    layers: dict[str, str] = {}
    for layer_name in (
        "routers",
        "services",
        "repositories",
        "clients",
        "schemas",
        "models",
    ):
        answer = _ask(f"  {layer_name}: ")
        if answer:
            layers[layer_name] = answer
    return layers


def _build_config_text(
    layers: dict[str, str],
    config_module: str,
    orm: str,
    http_client: str,
) -> str:
    lines = ["[tool.rivt]"]

    if config_module:
        lines.append(f'config_module = "{config_module}"')
    if orm:
        lines.append(f'orm = "{orm}"')
    if http_client:
        lines.append(f'http_client = "{http_client}"')

    lines.append("")

    for layer_name, path in layers.items():
        can_import = DEFAULT_CAN_IMPORT.get(layer_name, [])
        can_import_str = ", ".join(f'"{ci}"' for ci in can_import)
        lines.append(f"[tool.rivt.layers.{layer_name}]")
        lines.append(f'paths = ["{path}"]')
        lines.append(f"can_import = [{can_import_str}]")
        lines.append("")

    return "\n".join(lines) + "\n"


def _prompt_choice(question: str, options: list[str]) -> str:
    print(f"\n{question}:")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        answer = _ask("> ")
        if answer in {str(i) for i in range(1, len(options) + 1)}:
            return answer
        print(f"  Please enter 1-{len(options)}.")


def _ask(prompt: str, *, default: str = "") -> str:
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(1)
    return answer or default


# ---------------------------------------------------------------------------
# new-rule
# ---------------------------------------------------------------------------


def _run_new_rule(name: str) -> None:
    rules_dir = Path.cwd() / LOCAL_RULES_DIR
    rules_dir.mkdir(parents=True, exist_ok=True)

    file_name = name.replace("-", "_")
    file_path = rules_dir / f"{file_name}.py"

    if file_path.is_file():
        print(f"Error: {file_path} already exists.", file=sys.stderr)
        sys.exit(1)

    class_name = _to_class_name(name)
    file_path.write_text(_rule_template(class_name, name), encoding="utf-8")
    print(f"Created {file_path}")


def _to_class_name(name: str) -> str:
    parts = name.split("-")
    return "".join(word.capitalize() for word in parts) + "Rule"


def _rule_template(class_name: str, rule_id: str) -> str:
    return f'''\
"""Custom rule: {rule_id}."""

import ast
from pathlib import Path

from rivt import Rule, RivtConfig, Violation


class {class_name}(Rule):
    id = "{rule_id}"
    description = "{rule_id}"

    def check(
        self, tree: ast.Module, file_path: Path, config: RivtConfig
    ) -> list[Violation]:
        """Check a single file for violations.

        Args:
            tree: The parsed AST of the file.
            file_path: The file path relative to the project root.
            config: The rivt configuration. Use config.get_layer(file_path)
                to determine which architectural layer a file belongs to
                (e.g. "routers", "services", "repositories").

        Returns:
            A list of Violation objects. Each violation needs:
                rule_id: This rule\'s ID ("{rule_id}").
                path: str(file_path).
                line: The 1-based line number.
                col: The 0-based column offset.
                message: A human-readable explanation of the violation.
        """
        violations: list[Violation] = []
        # TODO: Implement your rule logic here.
        return violations
'''
