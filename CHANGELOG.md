# Changelog

WildINTEL project provides up-to-date release notes for `wildintel-trapper-sdk`. This document
contains information about recent changes, including new features, bug fixes, and improvements.
It is intended to help users and developers understand the evolution of the project over time.

You can find release notes and source distributions on the
[releases page](https://github.com/wildintelproject/wildintelproject-trapper-sdk/releases).

To report a bug or request a new feature, please open an
[issue](https://github.com/wildintelproject/wildintelproject-trapper-sdk/issues).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Upcoming release

## Released

### [0.1.0](https://github.com/wildintelproject/wildintelproject-trapper-sdk/releases/tag/v0.1.0) - 2026-07-21

### Added
- Write access for locations and deployments (`import_locations()`/`import_deployments()`), via the
  classic Trapper web UI's import forms over cookie/session authentication — the REST API is
  read-only for these two resources.
- `split`/`delay`/`chunk_size` options on `import_locations()`, `import_deployments()`, and
  `import_classifications()` to upload large CSVs in smaller, self-contained chunks instead of one
  request.
- Automatic retry (`retry_attempts`/`retry_min_wait`/`retry_max_wait`, via
  [tenacity](https://github.com/jd/tenacity)) on network-level upload failures (timeouts,
  connection resets) for all three import methods.
- `client.classification_results.import_classifications()` — imports expert/AI observations into a
  classification project via a real, token-authenticated REST endpoint.
- `client.locations.all()` as an alias of `where()`.
- Example scripts with sample CSVs for `import_locations`, `import_deployments`, and
  `import_classifications` (`examples/`).
- Per-component documentation guides (`docs/guide/`), a `Features` page, and an `About` page.

### Fixed
- `import_classifications()` no longer crashes with a raw `JSONDecodeError` when the server returns
  a non-JSON (HTML) error page for a genuine unhandled server-side exception; it now raises a clear
  `err.APIError` instead.
- `classificationTimestamp` empty-string values no longer raise a pydantic `ValidationError` in the
  classification/AI-classification export schemas.
- `research_project`/`timezone` are now required parameters of `import_locations()`/
  `import_deployments()`, preventing silent data corruption — a blank `timezone` previously created
  locations with an invalid value that later crashed unrelated requests with an unrelated-looking
  server error.
- `session_login()` now follows redirects when fetching the CSRF cookie, with an HTML-scraping
  fallback, fixing a "No csrftoken cookie found" failure on some server configurations.

### Changed
- Project renamed (distribution name only, package import stays `trapper_client`) to
  `wildintel-trapper-sdk`.
- Documentation restyled to match sibling WildINTEL projects (logo, colors, a "Documentation Map"
  on the index page).

