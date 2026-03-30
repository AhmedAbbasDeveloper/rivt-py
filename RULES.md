# Rules

## layer-imports

Enforces import boundaries between architectural layers. Each layer declares which other layers it can import from via `can_import` in the configuration.

The conventional import graph for FastAPI projects:

| Layer | Can import from |
| --- | --- |
| routers | services, schemas |
| services | repositories, clients, schemas |
| repositories | schemas, models |
| clients | schemas |
| schemas | (none) |
| models | (none) |

`rivt init` uses these conventions when generating your config. You control the final result — adjust `can_import` to match your architecture. Files not inside any configured layer are not checked.

### Violation

```python
# app/routers/users.py
from app.repositories.user import get_user_by_id
```

```
app/routers/users.py:2:0  layer-imports  Routers must not import from repositories. Import from services, schemas instead. (found: app.repositories.user)
```

Correct:

```python
# app/routers/users.py
from app.services.user import get_user
```

### Glob patterns

For feature-based / vertical slicing projects, configure layers with glob patterns:

```toml
[tool.rivt.layers.routers]
paths = ["src/**/router.py"]
can_import = ["services", "schemas"]

[tool.rivt.layers.services]
paths = ["src/**/service.py"]
can_import = ["repositories", "clients", "schemas"]
```

This matches `src/users/router.py`, `src/orders/router.py`, etc.

### Edge cases

- Relative imports are resolved against the file's location and checked the same way.
- Star imports (`from app.repositories import *`) are checked by their source module.

---

## library-imports

Restricts specific libraries to specific layers. This is separate from `layer-imports` — you can enable one without the other.

rivt auto-generates restrictions for `fastapi` (routers only) and for the libraries specified in `orm` and `http_client`. You can override or extend these via `[tool.rivt.libraries.*]` in your config.

### Violation

```python
# app/services/order.py
from fastapi import HTTPException
```

```
app/services/order.py:2:0  library-imports  Services must not import fastapi. Raise a domain exception and handle it in the router layer. (found: fastapi.HTTPException)
```

Correct:

```python
# app/services/order.py
from app.exceptions import OrderError

raise OrderError("Cannot cancel shipped order")
```

### Configuration

```toml
[tool.rivt.libraries.sqlalchemy]
allowed_in = ["repositories", "models"]

[tool.rivt.libraries.fastapi]
allowed_in = ["routers"]
```

---

## no-env-vars

`os.environ`, `os.getenv()`, and `os.environ.get()` must not be used outside the configured config module(s).

### Violation

```python
# app/services/email.py
import os
api_key = os.getenv("SENDGRID_API_KEY")
```

```
app/services/email.py:2:10  no-env-vars  Do not access environment variables directly. Read from the config module instead (app/core/config.py).
```

Correct:

```python
# app/services/email.py
from app.core.config import settings
api_key = settings.sendgrid_api_key
```

### Configuration

```toml
[tool.rivt]
config_module = "app/core/config.py"

# Or multiple:
config_module = ["app/core/config.py", "app/core/settings.py"]

# Or glob:
config_module = ["app/core/*.py"]
```

---

## response-model

Route handlers must declare their response type — either via `response_model` in the decorator or a return type annotation.

Both valid:

```python
@router.get("/users/{id}", response_model=UserResponse)
def get_user(id: int): ...

@router.get("/users/{id}")
def get_user(id: int) -> UserResponse: ...
```

Violation — neither present:

```python
@router.get("/users/{id}")
def get_user(id: int): ...
```

```
app/routers/users.py:2:0  response-model  Add response_model to the @router.get() decorator or a return type annotation (e.g. -> UserResponse).
```

---

## status-code

POST and DELETE handlers must declare an explicit `status_code`. GET, PUT, and PATCH are excluded — the implicit 200 is almost always correct. POST and DELETE are the methods where the status code is a design decision.

### Violation

```python
@router.post("/users", response_model=UserResponse)
def create_user(data: CreateUserRequest): ...
```

```
app/routers/users.py:2:0  status-code  Add status_code to the @router.post() decorator (e.g. status_code=201).
```

---

## http-timeout

Outbound HTTP calls must specify a `timeout` parameter. Missing timeouts cause cascading failures when a downstream service is slow.

Checks two patterns:

**Direct calls** — `httpx.get()`, `httpx.post()`, etc.:

```python
response = httpx.get("https://api.stripe.com/v1/charges")
# violation: Add timeout parameter to httpx.get() (e.g. timeout=10).
```

**Client construction** — `httpx.Client()`, `httpx.AsyncClient()`:

```python
client = httpx.Client()
# violation: Add timeout parameter to httpx.Client() (e.g. timeout=10).
```

Method calls on client instances (`client.get(...)`) are not flagged — the timeout is expected on the constructor.

---

## Custom rules

These 6 rules cover universal conventions. The real power is rules specific to your team. Scaffold one with `rivt new-rule <name>` and tell your agent what to enforce — see the [custom rules guide](CONFIGURATION.md#custom-rules).
