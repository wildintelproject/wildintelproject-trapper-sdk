# Features

## Reading data

- **One component per resource** — each Trapper endpoint (locations, deployments, resources,
  collections, research projects, classification projects, classifications, AI classifications,
  ...) has its own class with a consistent interface.
- **Six access patterns on every component** — `get()` for one page, `get_all()`/`all()` to merge
  every page into a single result, `where()` for lazy, on-demand pagination, `find(pk)` for a single
  item, and `export()` to dump results straight to a CSV file. See [Usage](usage.md).
- **Transparent pagination** — `where()` fetches pages as you iterate; `get_all()` walks every page
  for you and merges the results, so you never have to write a page-number loop by hand.
- **Filtering via keyword arguments** — every component documents its own filter fields (date
  ranges, PKs, free-text search, ...), passed straight through as query parameters.
- **CSV export** — any component's results can be written directly to a CSV file with a single
  `export(file=...)` call, or returned as a list of typed model instances when `file=None`.

---

## Typed models

- **Pydantic v2 for every response** — full IDE autocompletion, and validation errors surface
  immediately instead of failing later on a missing/mistyped field.
- **CamtrapDP and Trapper-flavoured schemas** — endpoints that can return either shape (e.g.
  classification/AI-classification export rows) are modeled as a `Union` and resolved automatically
  based on which fields are present.
- **Defensive field validators** — optional fields that the server sometimes sends as an empty
  string instead of omitting (dates, numbers, booleans) are normalized to `None` rather than raising
  a `ValidationError`.

---

## Write access where the REST API falls short

- **Classification import — a real, token-authenticated REST endpoint** —
  `client.classification_results.import_classifications()` posts a CSV to
  `media_classification/api/classifications/import/` to re-apply expert/AI classification data
  (species, count, approval, ...) to existing observations, matched by their internal `_id`.
- **Locations/deployments import — a documented workaround** — the REST API is read-only for these
  two resources, so `client.locations.import_locations()`/`client.deployments.import_deployments()`
  simulate the classic web UI's own import forms via cookie/session authentication instead of the
  API's token auth. This is explicitly **not** a stable API contract — see each component's guide
  for the caveats before relying on it.
- **Chunked uploads for large CSVs** — all three import methods accept `split`/`delay`/`chunk_size`
  to break a large CSV into several smaller, self-contained chunks (each repeating the header row),
  uploaded one at a time with a delay in between — a workaround for servers that reject or time out
  on very large single-file uploads.
- **Automatic retry on network-level failures** — `retry_attempts`/`retry_min_wait`/`retry_max_wait`
  retry a chunk/file upload (via [tenacity](https://github.com/jd/tenacity), exponential backoff)
  when the request fails with a timeout or connection error — the failure mode expected when a
  chunk is still too large or slow for the server. HTTP error responses (validation failures) are
  never retried, since a retry can't fix those.

---

## Authentication

- **Static access token** — `access_token="<token>"`, sent as a `Token` header on every API call.
- **Username/password** — `user_name`/`user_password`, used both for basic/session API auth and for
  the cookie/session login required by the locations/deployments import workaround.
- **Session login for classic web views** — `APIClientBase.session_login()` handles the CSRF
  token/cookie dance transparently (including an HTML-scraping fallback when the cookie isn't set
  the way expected), so the write-access components above can authenticate against Django's own
  login form.

---

## Error handling

- **Mapped exception types** — `err.NotFoundError`, `err.BadRequestError`, `err.UnauthorizedError`,
  `err.ForbiddenError`, `err.ConflictError`, `err.UnprocessableEntityError`, and a generic
  `err.ServerError`/`err.APIError`, chosen from the response status code.
- **Real server error details, not just a status code** — where the server embeds structured
  validation errors (Django form errors, a [frictionless](https://framework.frictionlessdata.io/)
  table-validation report embedded as JSON for a JS widget, ...), the SDK parses them out into the
  exception message instead of surfacing a generic banner.
- **Never crashes on an unexpected non-JSON response** — a genuine unhandled server error (an HTML
  error page instead of the expected JSON body) is detected and turned into a clear `err.APIError`
  with a text snippet, rather than an opaque `JSONDecodeError`.

---

## Testing

- **Three test layers** — `unit` (fully mocked, no network), `integration` (mocked HTTP responses
  exercising more of the stack), and `e2e` (smoke tests against a real Trapper instance, opt-in via
  `WILDINTEL_SMOKE_ENABLED=1`). See [Testing](testing.md).
- **A shared base test class** (`ComponentUnitTestBase`) exercises the six access patterns
  consistently across every component, so a new component gets that coverage for free.
