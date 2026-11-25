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

## Deploy Trapper v1, v2 and v2-ninja, seed a dataset and run the e2e tests

`uv run cli trapper` gives the end-to-end tests something to run against: it deploys Trapper with Docker Compose, always
with the same accounts, seeds it with a test dataset and runs `tests/e2e` with the variables that dataset needs. It needs
Docker and (the first time) a network to the registry. It does **not** deploy Trapper AI or the citizen science
frontend: those are other containers.

| Instance | Image | nginx | API |
|---|---|---|---|
| `v1` | `trapper:latest` (1.7.4) | `8080` | the old one (DRF) |
| `v2` | `trapper:2.0.0a2` | `8180` | the old one (DRF) |
| `ninja` | `trapper:refactor-api-ninja` (2.0.0a4) | `8280` | the new one (`/api/v2/`, Django Ninja), and the old one |

<div class="termy">

```console
$ uv run cli trapper up                            // the three (or: up v1 | up v2 | up ninja)
$ uv run cli trapper seed v2 --dataset 1           // or --dataset 2, or --dataset all
$ uv run cli trapper e2e v2 --dataset 1            // tests/e2e against it
$ uv run cli trapper e2e v2 --dataset 1 -- -k species -x    // after --: options for pytest
$ eval "$(uv run cli trapper env v2 --dataset 1)"  // or the variables, to run pytest yourself
$ uv run cli trapper status | logs v2 trapper-celery | down | destroy
```

</div>

- **The datasets** (`dev/trapper/seed/dataset<N>.py`), seeded with the SDK where Trapper has a way in and with
  `manage.py shell` where it has none. Seeding again changes nothing.
    - **1, "Mamíferos de Doñana y Sierra Morena"**: small and hand-made. 6 locations, 7 deployments, 26 images in two
      collections of one classification project (a Citizen Science one on v2, slug `mamiferos-donana-sm`), 9 species,
      22 approved classifications with sex and age, blanks and humans, 4 pending (3 with classifications by an expert
      and a collaborator that disagree), 2 AI classifications with boxes.
    - **2, "Cabañeros 2025"**: more than 500 rows in several lists, to see what paging does. 12 locations, 14
      deployments, 640 images in bursts of three in two collections and two classification projects, 12 species, 600
      user classifications (55 pending) with blanks, humans, vehicles, counts, boxes; 66 AI rows from two providers.
- **The e2e variables**: `env --dataset N` and `e2e --dataset N` read the primary keys from the instance through the SDK
  (the dataset's project and collection, a location with a resource of it, a user classification, ...), so the tests
  that need them run instead of skipping. Without `--dataset`, `env` gives only the URL and the credentials.
- **One dataset per instance** keeps the results apart: both can be seeded in one instance, but some tests read the
  whole server. Use `--name` for another instance of the same version, with its own `--port-offset`:
  `uv run cli trapper up v1 --name ds1 --port-offset 3000`, then the same options for `seed`, `env` and `e2e`.
- **The branch** (`--branch`, or `--v1-branch`, `--v2-branch`, `--ninja-branch`) is the tag of the image
  `registry.gitlab.com/trapper-project/trapper:<branch>`: the name as you give it (`2.0.0a2`, `latest`) or the one the
  Trapper CI gives to a branch (`refactor/api-ninja` is `refactor-api-ninja`). The command checks that the image exists.
  It does not build Trapper from source.
- **Names**: each instance is the compose project `wildintel-sdktest-trapper-<name>` (`v1`, `v2`, `v2-ninja`,
  `v1-ds1`, `v2-p1000`, ...), so `docker ps` tells the test instances apart. `--port-offset N` adds `N` to every port
  and, without `--name`, names the instance `<version>-p<N>`.
- **Ports** (add `--port-offset`): use nginx (without it a file download answers `200` with no body); the app is on
  `8010`/`8100`/`8200` and the uploader on `8088`/`8188`/`8288` (v1/v2/ninja).
- **Accounts** (password `wildintel-sdk-test`; Trapper v1 logs in with the e-mail, `<user>@example.org`): `sdktest`
  (superuser, the one the API token is for), `rp_staff` (staff and superuser), `rp_user`, `ana`, `luis` and `plainuser`,
  each with a token (also for the new API), and the research project `SDKT` with `sdktest` and `rp_staff` as admins,
  `ana` as expert and `luis` and `rp_user` as collaborators. Running `up` again leaves them as they are.
- `down` stops the instance and keeps its data; `destroy` deletes the data too. The secrets, the tokens and what was
  seeded are in `dev/trapper/.state/<name>/`, which git does not track.
- **Memory**: an instance takes about 2–2.5 GB; stop the ones you are not using.

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
