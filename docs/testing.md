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

## Deploy Trapper v1 and v2 to test against

`uv run cli trapper` deploys one Trapper v1 and one Trapper v2 with Docker Compose, always with the same accounts, so
that the end-to-end tests have something to run against. It needs Docker and (the first time) a network to the
registry. It does **not** deploy Trapper AI or the citizen science frontend: those are other containers.

<div class="termy">

```console
$ uv run cli trapper up                            // v1 and v2 (v1: latest, v2: 2.0.0a2)
$ uv run cli trapper up v2 --branch development     // another branch of Trapper
$ uv run cli trapper up --port-offset 1000          // another instance: ports + 1000, its own containers and data
$ eval "$(uv run cli trapper env v2)"               // WILDINTEL_* for the e2e tests
$ uv run cli test e2e
$ uv run cli trapper status | logs v2 trapper-celery | down | destroy
```

</div>

- **The branch** is the tag of the image `registry.gitlab.com/trapper-project/trapper:<branch>`: the name as you give it
  (`2.0.0a2`, `latest`) or the one the Trapper CI gives to a branch (`refactor/api-ninja` is `refactor-api-ninja`). The
  command checks that the image exists. It does not build Trapper from source.
- **Several instances**: `--port-offset N` adds `N` to every port and makes **another instance** (its own containers, volumes,
  subnet and accounts), which lives next to the others. The other commands need the same `--port-offset` to find it
  (`uv run cli trapper env v2 --port-offset 1000`).
- **Ports** (add `--port-offset`): v1 on `8080` (nginx, the one to use: without it a file download answers `200` with no
  body), `8010` (the app) and `8088` (uploader); v2 on `8180`, `8100` and `8188`.
- **Accounts** (password `wildintel-sdk-test`; Trapper v1 logs in with the e-mail, `<user>@example.org`): `sdktest`
  (superuser, the one the API token is for), `rp_staff` (staff and superuser), `rp_user`, `ana`, `luis` and `plainuser`,
  each with a token, and the research project `SDKT` with `sdktest` and `rp_staff` as admins, `ana` as expert and `luis`
  and `rp_user` as collaborators. Running `up` again leaves them as they are.
- `down` stops the instance and keeps its data; `destroy` deletes the data too. The secrets and the tokens are in
  `dev/trapper/.state/`, which git does not track.
- **What an instance does not have yet**: locations, deployments, images and classifications. The tests that need them
  skip or fail on an empty server (for example, an export of locations answers `400` when there are none, as Trapper does).

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
