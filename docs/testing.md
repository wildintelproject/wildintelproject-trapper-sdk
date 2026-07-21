# Testing

The test suite is split into three layers:

| Marker | Description | Requires a server? |
|--------|-------------|-------------------|
| `unit` | Pure unit tests — all HTTP calls are mocked | No |
| `integration` | Component tests with mocked HTTP responses | No |
| `e2e` | Smoke tests against a real Trapper instance | Yes |

The repository also ships a small `cli.py` that wraps `pytest` with these markers, so you don't need to remember the `-m`/`-k` flags:

<div class="termy">

```console
$ uv run cli test unit
╭──────────── wildintel-trapper-sdk — tests ────────────╮
│ Suite: unit   Marcador: -m "unit"                      │
╰─────────────────────────────────────────────────────────╯
................................................... [100%]
1100 passed in 2.10s
```

</div>

## Run unit and integration tests

<div class="termy">

```console
$ uv run cli test all
// Equivalent to:
$ uv run pytest tests -m "unit or integration" -q
```

</div>

## Run only unit tests

<div class="termy">

```console
$ uv run cli test unit
// Equivalent to:
$ uv run pytest tests/unit -q
```

</div>

## Run end-to-end tests

E2E tests hit a live Trapper server. Set the following environment variables before running them:

```bash
export WILDINTEL_SMOKE_ENABLED=1
export WILDINTEL_BASE_URL="https://your-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"        # or use user/password below
export WILDINTEL_USER_NAME="user"
export WILDINTEL_USER_PASSWORD="password"
export WILDINTEL_VERIFY_SSL=1                  # set to 0 to skip SSL verification
export WILDINTEL_TIMEOUT=30
```

Then run:

<div class="termy">

```console
$ uv run cli test e2e
// Equivalent to:
$ uv run pytest tests/e2e -m e2e -q
```

</div>

You can also copy `tests/env.example` to `tests/.env` and fill in the values — pytest will load it automatically.

## Filter by keyword or get verbose output

<div class="termy">

```console
$ uv run cli test unit -k import_locations -v
```

</div>

## Coverage

<div class="termy">

```console
$ uv run pytest tests -m "unit or integration" --cov=src/trapper_client --cov-report=term-missing
```

</div>
