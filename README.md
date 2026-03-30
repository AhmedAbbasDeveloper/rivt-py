# rivt

Your architecture, enforced.

Code that compiles, passes type checking, and lints clean can still be architecturally wrong — the ORM leaking into routers, `os.getenv()` scattered across a dozen files, response types missing on every endpoint. Agents make it worse. They write fast, don't remember your conventions, and will pass every check you have in place.

rivt catches what ruff and pyright can't: layer boundaries, library placement, framework conventions. It ships with rules for universal best practices, and you can create your own for your team's specific patterns. Every violation tells you exactly what to fix. Hook it into your agent's workflow and violations get fixed automatically, before the code ever reaches you.

```
app/routers/users.py:5:0    layer-imports     Routers must not import from repositories. Import from services, schemas instead. (found: app.repositories.user)
app/services/order.py:3:0   library-imports   Services must not import fastapi. Raise a domain exception and handle it in the router layer. (found: fastapi.HTTPException)
app/services/email.py:4:14  no-env-vars       Do not access environment variables directly. Read from the config module instead (app/core/config.py).
app/clients/stripe.py:9:22  http-timeout      Add timeout parameter to httpx.Client() (e.g. timeout=10).

Found 4 violations in 4 files.
```

## Agent integration

Set it up once. Violations get fixed before you see the code.

`.cursor/hooks.json`:
```json
{
  "version": 1,
  "hooks": {
    "stop": [{ "command": ".cursor/hooks/run-rivt.sh" }]
  }
}
```

`.cursor/hooks/run-rivt.sh`:
```bash
#!/bin/bash
input=$(cat)
status=$(echo "$input" | jq -r '.status // empty')

if [[ "$status" != "completed" ]]; then
    echo '{}'
    exit 0
fi

output=$(rivt check 2>&1)
exit_code=$?

if [[ $exit_code -ne 0 ]] && [[ -n "$output" ]]; then
    followup=$(jq -n --arg msg "rivt found architectural violations. Fix them:\n\n$output" \
        '{"followup_message": $msg}')
    echo "$followup"
else
    echo '{}'
fi

exit 0
```

Make the script executable with `chmod +x .cursor/hooks/run-rivt.sh`. Pre-commit hooks and CI checks work too — rivt exits `1` when violations are found.

## Install

```
pip install git+https://github.com/AhmedAbbasDeveloper/rivt-py.git
```

Requires Python 3.11+. Works with pip, Poetry, and uv.

## Quick start

```bash
rivt init      # detects your project layout, writes config in pyproject.toml
rivt check     # find violations
```

`rivt init` scans your project for conventional directory names (routers, services, repositories, etc.) and generates a complete `[tool.rivt]` section — every layer, every import rule, ready to review and adjust.

Exit codes: `0` clean, `1` violations found, `2` config error.

## Rules

rivt ships with rules for architectural concerns that ruff, pyright, and mypy structurally cannot check:

| Rule | What it enforces |
| --- | --- |
| `layer-imports` | Import boundaries between architectural layers |
| `library-imports` | Libraries restricted to specific layers |
| `no-env-vars` | No `os.getenv()` / `os.environ` outside the config module |
| `response-model` | Route handlers must declare a response type |
| `status-code` | POST/DELETE handlers must declare `status_code` |
| `http-timeout` | HTTP calls must specify a `timeout` |

All rules are on by default. Disable any with `disable = ["status-code"]`. See [RULES.md](RULES.md) for examples and rationale.

## Configuration

All config lives in `pyproject.toml` under `[tool.rivt]`. Each layer declares where its files live (`paths`) and which other layers it can import from (`can_import`):

```toml
[tool.rivt]
config_module = "app/core/config.py"
orm = "sqlalchemy"
http_client = "httpx"

[tool.rivt.layers.routers]
paths = ["app/routers"]
can_import = ["services", "schemas"]

[tool.rivt.layers.services]
paths = ["app/services"]
can_import = ["repositories", "clients", "schemas"]

[tool.rivt.layers.repositories]
paths = ["app/repositories"]
can_import = ["schemas", "models"]

[tool.rivt.layers.schemas]
paths = ["app/schemas"]
can_import = []

[tool.rivt.layers.models]
paths = ["app/models"]
can_import = []
```

Your config file is the source of truth. What you see is what rivt enforces — no hidden rules, no implicit behavior. Glob patterns work for feature-based layouts (`paths = ["src/**/router.py"]`). See [CONFIGURATION.md](CONFIGURATION.md) for the full reference.

## Custom rules

The built-in rules cover universal conventions. The real power is rules specific to your team — every repository method must have an error handler, every service must be async, every route needs auth middleware. Whatever your team cares about, codify it.

```bash
rivt new-rule handle-db-errors
# Created .rivt/rules/handle_db_errors.py
```

The rule API is simple enough for your agent to write. Scaffold the file, tell your agent what to enforce, and run `rivt check`. rivt auto-discovers rules from `.rivt/rules/`. For rules shared across repos, publish a package with entry points. See [CONFIGURATION.md](CONFIGURATION.md#custom-rules) for examples and the full guide.

## Adopting in an existing codebase

Running rivt on a large codebase will surface many violations. Adopt progressively:

1. **Start with a few rules.** Disable the rest with `disable = [...]`.
2. **Narrow the scope.** Exclude directories with `exclude = [...]`.
3. **Add to CI.** Enforce on new code immediately.
4. **Clean up over time.** Re-enable rules as you fix violations.

Also available for [JavaScript / TypeScript (React)](https://github.com/AhmedAbbasDeveloper/rivt-js).
