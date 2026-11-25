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

### Added
- **The new API of Trapper 2** (`/api/v2/...`, branch `refactor-api-ninja`; issue #129, phase 1 of #99):
  `trapper_version="ninja"`, or auto-detected on a v2 server that serves `GET api/v2/probe/auth/`; `server_version`
  stays `"v2"` and the new `client.api_flavor` is `"legacy"` or `"ninja"`. The read lists use the new routes
  (locations, deployments, resources, collections, research and classification projects and their collections,
  classificators, final/user/AI classifications, classifications map, sequences, species, users), ordered by `pk`
  unless `sort_by` is given; the other routes still go through the old ones, which Trapper serves too. A component
  declares a route of the new API with `versioned(old, ninja=new)`; `ninja_broken_filters` lists the filters that fail
  there. With `trapper_version="auto"` the first call of a list now learns which API to use (one or two requests,
  cached): pass `trapper_version` to skip them.
- `classification_package.download_package()` and `download_project_package()` (issue #111): save the Camtrap DP
  zip (streamed, retried, `.part` file), instead of calling `make_request` on the URL.
- `ClassificationResultsComponent` (issue #100): the class of `client.classification_results`, under a name that says what it reads. It is
  the same class as `ClassificationsComponent`, which stays.
- `uv run cli trapper up|down|destroy|status|logs|env` (issue #101): deploys a Trapper v1 and a Trapper v2 with Docker Compose (the files are
  in `dev/trapper/`), always with the same accounts (`sdktest`, `rp_staff`, `rp_user`, `ana`, `luis`, `plainuser`, with tokens) and the
  research project `SDKT`. `--branch` is the tag of the image of Trapper (`latest`, `development`, `refactor-api-ninja`...), also
  `--v1-branch` and `--v2-branch`; `--port-offset N` makes another instance next to the others; `env` prints the `WILDINTEL_*` variables
  of the e2e tests. Without Trapper AI and the citizen science frontend. The test data (locations, deployments, images and
  classifications) is not deployed yet.
- The batch downloads of `classification_media` (issue #95) return a `DownloadedFiles`: still the list of the downloaded paths,
  with `.failed` (`{media id: message}`), `.skipped` and `.ok`, and the failures are logged. They used to be swallowed: with the
  default `private_human` two private files were left out and nothing said so. New `on_error="raise"` and `skip_existing=True`
  (both default to the old behaviour). The Pydantic serializer warnings of every download are gone.
- `UnknownFilterWarning` for `client.classification_results` and `client.classification_media` (issue #85): they name a filter
  that the server version ignores (`user`, `feedback`, `confidence` and `ai_provider` are not filters of these lists) and
  `private_species`, which makes Trapper answer `500`; and `approved=True` works on Trapper v1, where the filter is called
  `status`, so one name serves both versions.
- **Trapper v2 support** (issue #1). `TrapperClient(trapper_version="auto" | "v1" | "v2")`: with
  `"auto"` (default) the version is detected once, on first use, from
  the public `GET api/cs/version/` (major number of the release), falling back to probing
  `GET storage/api/upload-auth/` (404 → v1; 200/401/403 → v2). Read it with `client.server_version`
  and the exact release with `client.server_release`.
- `client.upload_auth()` (v2): checks that the token may upload packages before sending data.
- `TusUploader` (`trapper_client.components.tus_uploader`): resumable uploads through tusd (tus 1.0),
  the v2 replacement for the v1 chunked uploader. `client.get_uploader()` returns the right uploader
  for the server's version.
- Components that Trapper v2 removed — `maps`, `locations_geojson`, `collections.*_ondemand` —
  raise `UnsupportedVersionError` on a v2 server instead of failing with a bare 404.
- `locations.import_locations()` and `deployments.import_deployments()` work on v2 too, through the
  import actions of its Django admin (`admin/geomap/<location|deployment>/import-*/`). Same signature;
  they need a staff account with the add permission, and v2 processes the import asynchronously (a
  `True` result means the table was validated and queued, not that every row is already in the
  database). Failures report the server's message and the per-row validation errors. A redirect to
  the login page is no longer taken as success.
- `deployments.geojson()` (Trapper v2): deployments as a GeoJSON `FeatureCollection`, filtered by
  `classification_project`, `observation_type`, `species` and date range. It is the v2 replacement for
  `maps` / `locations_geojson`.
- Schemas of classification projects, classification results, the classifications map, classificators
  and user classifications now parse Trapper v2 payloads (`null` UI links and profiles, no
  `status`/`status_ai`/`classification`, attributes wrapped as `{"value": ...}`); v1 payloads still
  parse. They raised `ValidationError` on v2 before.
- `classification_results.import_classifications(overwrite_attrs=True)` raises `UnsupportedVersionError`
  on v2, whose import endpoint no longer reads the option (it used to be dropped silently). The rest
  of the import is the same REST endpoint in both versions.
- A classification import whose table fails validation makes Trapper answer a bare HTTP 500 (it cannot serialize
  its validation report; v1 and v2 alike). The `APIError` now says so and lists what to check.
- `import_classifications(check_table=True)` checks the table locally before sending it (`_id` and
  `classificationMethod` columns present, `sex` only `female`/`male`) and raises a `ValueError` naming
  the problem, instead of letting Trapper answer with a bare 500. `check_table=False` skips it.
- `client.project_deployments` (Trapper v2): the deployments of a classification project
  (`api/deployments/<slug>/`) — list, `locations`, `find`, `update` (PATCH), `delete`,
  `update_timestamps`, AI `progress`, and the depth-calibration / distance-estimation requests.
- `locations.wait_for_import(ids)` / `deployments.wait_for_import(ids)`: wait until an imported
  table is visible through the API. Trapper v2 imports asynchronously and neither version has an API to
  query the import task, so it polls for the rows themselves.
- `deployments.by_collection_with_counts()`: the deployments with at least one resource in a
  collection, each with how many resources it has there.
- **Documentation in English and Spanish** (`mkdocs-static-i18n`, suffix structure: `page.md` is
  English, `page.es.md` Spanish; the API reference stays English-only). Every guide now states which
  Trapper versions it supports, `deployments.geojson()` is documented in the deployments guide, and
  the home page says the SDK covers Trapper v1 and v2.
- `research_projects.create(ResearchProjectCreate(...))` (Trapper v1): creates a research project
  through the classic web form, since the REST API is read-only for it. `ResearchProjectCreate` is a
  Pydantic model with every field of the form, validated before anything is sent. Returns the project, or `None` when the account is
  not staff and the project awaits approval. Form errors now name the invalid field
  (`name: ... already exists`) instead of the generic banner, for every form-based write.
- `trapper_client.SamplingDesign`, `SensorMethod`, `AnimalTypes` and `BaitUse`: enumerations of the
  fixed choices of the research project form; the request model accepts a member, its number or its label.
- `classification_projects.create()`, `.add_collections()` and `.remove_collection()` (Trapper v1):
  create a classification project, link storage collections to it and unlink them, through the
  classic web forms (the REST API is read-only for them). `create()` takes a
  `ClassificationProjectCreate` model. A project can only use the collections of its research
  project; unlinking deletes the classifications made on that collection in the project.
- `classificators.create(ClassificatorCreate(...))` (Trapper v1): creates a classificator through the
  classic web form: layout (`ClassificatorTemplate`), the species it offers and the ones Trapper
  watches, and the optional attributes. Custom and predefined attributes are not covered.
- `ResearchProjectCreate(members=[ResearchProjectMember(user, role)])` (Trapper v1): the users that
  join a research project when it is created, with the role they have in it
  (`ResearchProjectRoleType`: admin, expert or collaborator). `user` is a `User` or its primary key.
  Enumeration labels are now matched in any case.
- `ClassificationProjectCreate(members=[ClassificationProjectMember(user, role)])` (Trapper v1): the
  users that join a classification project when it is created, with their role
  (`ClassificationProjectRoleType`: admin, expert, collaborator, error proof or citizen).
- `Location.longitude` and `Location.latitude`: the coordinates of a location as numbers. Trapper returns them as
  one string (`"-6.44, 37.05"`, longitude first, in v1 and v2); `coordinates` keeps it as it comes. They are
  `None` when the string is missing, cannot be read or is out of range.
- `deployments.wait_for_update({deployment_id: {field: value}})` (issue #47): waits until an update import
  (`import_deployments(update=True)`) has been applied. The import returns `True` when the table is queued and
  `wait_for_import()` cannot tell an update, because the IDs exist already. The guide now describes the round trip
  export (`raw=True`), edit, import with `update=True`, checked on v1 and v2.
- `client.deployments.in_area(bbox=..., center=..., radius=..., **filters)` (issue #51): the deployments whose
  location is inside a bounding box or a circle. A deployment has no coordinates of its own, so it finds the
  locations in the area (`locations.in_area()`) and asks for their deployments in batches of location pks.
- `client.resources.download(pk, file, kind="original" | "preview" | "thumbnail")` (issue #56): saves the file of a
  resource. The API token cannot fetch it (the web view answers `404`), so it logs in with `user_name` and
  `user_password`, streams to a `.part` file, and retries network failures and `502`/`503`/`504` with tenacity.
- `deployments.download_resources(deployment_pk, directory, ...)` and `collections.download_resources(collection_pk,
  directory, ...)` (issue #69): download the files of a deployment or a collection into a folder, one `download()` per
  resource, with the filters of the resource list and a `filter_fn` to choose which ones, `skip_existing` so a run can
  be repeated, a failure that does not stop the rest, a progress callback and a `DownloadReport`. Both use
  `resources.download_many()`, which takes any list of resources.
- Creating a collection from a package is described and tested (issue #67): upload a YAML and a ZIP with the uploader,
  `collections.trigger_collection()`, and wait for the collection to appear. The guide has the YAML format, what the
  package needs and the gotchas (v1 needs Trapper's nginx for the uploader, and on v2 the first trigger can answer
  `NotFoundError` until the files are in place). An e2e runs the whole path on v1 and v2.
- Resource list filters (issue #58): `pk`, `locations_map`, `collections`, `deployments`, `tags` and `species` take a list
  or a comma-separated string and are sent the way Trapper reads each one (`deployments="1,2"` used to be ignored
  and return every resource, `collections="2,3"` was a `400`). `UnknownFilterWarning` also on the resource list
  (`locations_map` only on v1), and it names `deployment__isnull`, which Trapper answers with a `500`.
- Collection list filters (issue #63): `pk`, `owners`, `research_projects` and `locations_map` take a list or a
  comma-separated string and are sent the way Trapper reads each one (`pk=[2, 1]` kept one pk). New `CollectionStatus`
  enumeration: `status` is resolved in any case and refused with a `ValueError` if it is none of `Private`, `OnDemand`,
  `Public`, `Archived`, since Trapper answers a wrong one with an empty result. `UnknownFilterWarning` on the
  collection list too (`locations_map` only on v1).
- `client.locations.in_area(bbox=..., center=..., radius=..., **filters)` (issue #34): the locations inside a
  bounding box or a circle (radius in metres). Trapper v1's list ignores `in_bbox` and `radius` silently and
  v2's ignores `radius`, so the SDK filters on the client; on v2 a box is also sent as `in_bbox` (issue #40) so
  that fewer pages are read, and on v1 it reads every page that matches the other filters.
- `UnknownFilterWarning` (issue #37): the locations list ignores a filter it does not know without an error, so
  passing one (a typo, `radius`, `ordering`, or `country` on v2) now warns and names it. The filters are those
  each Trapper version applies, checked live; the request is still sent.
- `UnknownFilterWarning` also on the deployments list (issue #45), with the filters each Trapper version applies
  (`in_bbox` only on v2). `colls` and the like are named instead of silently returning every deployment.
- `export(file=..., raw=True)` (issue #36): saves the CSV exactly as Trapper sends it, with its own header,
  column order and values, instead of the SDK's column names sorted alphabetically. `False` by default, so
  nothing changes; it needs `file`.

### Changed
- The docstring of `ClassificationsComponent` (issue #97) no longer says AI classifications: it says what the component returns
  (the final classifications, in three shapes) and lists the filters that apply.
- The classification media guide and docstring say that `collection` is the pk of the link between the project and the collection, not
  the collection's (issue #93). It is not translated, because `wildintel-zooniverse` passes the link's pk to `where_project_media()`:
  use `where_collection_media()` to give the collection's.
- An empty results table or media table (`400 "Empty queryset or you have no permission..."`) is an empty result in
  `classification_results` and `classification_media` (issue #91): `get_*` has `count` 0, `where_*` iterates nothing,
  `export_*` gives `[]` or an empty file and the downloads give `[]`, as the classification list does. It used to be a
  `BadRequestError`. A missing permission is the same `400`, so it looks empty too; any other `400` is still an error.
- `classification_results.get()`, `get_all()`, `where()` and `all()` raise a `ValueError` when `deployment` or `collection` is given
  without `project` (issue #89): Trapper answers `400 "Select a valid choice"`, which reads as if the deployment did not exist.
- The classifications guide (issue #83) says that a classification is a set of observations, how several things in one image
  are handled (several observations sharing the `_id`), that `observationID` is only a row number, how boxes are stored in
  v1 (a list) and v2 (one box), and what happens when several users classify one image (checked with three users).
- The classifications guide (issue #81) says what `classification_results` represents (the final classification of each
  resource and its three views: list, results table and import), corrects the filter table (`user`, `feedback`,
  `confidence` and `ai_provider` are ignored; `approved` is v2 only and v1 uses `status`; `deployment` and `collection`
  need `project`) and explains that editing goes through the export with `camtrapdp=False` and the import.
- The classification media guide (issue #76) says what the component represents (the media table of a
  classification project: its eleven columns, how it arrives, public and private files) and describes the
  `private_*` parameters as they work: `True` hides the files of humans and vehicles, and Trapper reads only the
  exact text `True`.
- The classification media guide (issue #79) has an example of treating humans and vehicles as private or public,
  and says that `private_species` answers `500` with any value (checked on v1 and v2).
- **`Resource.date_recorded` is a `datetime`** (issue #60), like the dates of a deployment: timezone-aware, `None` when
  empty, the original text when it cannot be read. Code that used it as a string has to format it. The reader moved to
  `schemas/base.py` (`read_datetime`) and both schemas use it.
- **`deployment__isnull` is no longer documented as a resource filter** (issue #58): Trapper answers `500` to it on v1
  and v2. The SDK warns when it is passed.
- **The dates of a deployment are `datetime`** (issue #49): `Deployment.start_date`/`end_date` and
  `DeploymentExport.start_date`/`end_date` were text, and the JSON and the CSV spell them differently
  (`+01:00` and `+0100`). Both are timezone-aware `datetime` now; one that cannot be read stays as text and an
  empty one is `None`. Code that used them as strings has to format them, and `export(file=...)` writes them
  as ISO text with the colon.
- **The schemas the API returns are named after the resource.** The `Record` suffix is gone:
  `SpeciesRecord` is now `Species`, `ClassificatorRecord` is `Classificator`, `ClassificationRecord`
  is `Classification`, and likewise `User`, `Sequence`, `Map`, `UserClassification`,
  `AIClassification`, `ClassificationMap`, `ClassificationAgg` and `Media`.
  `ClassificationResourceRecord` is now `ClassifiedResource`, because `ClassificationResource` was
  already taken by the resource embedded in a classification. The old names still import (from the
  package, from `trapper_client.schemas` and from their module), are the same classes and raise a
  `DeprecationWarning`; they will be removed in a future release. The export row schemas
  (`ClassificationRecordExport`, ...) keep their names.

### Fixed
- The resource and species lists repeat and skip rows when paged on the old routes, like the classification list
  (issue #132): the workaround of #108 is now `TrapperComponent.unstable_order`, set on the three (pages of 500,
  repeated rows dropped, `UnstableOrderWarning`), and off on the new API, ordered by `sort_by=pk`.
- `classification_projects.*_collection_resources()` failed on Trapper v2: `classification_data.url` is `null` there
  (issue #129).
- The final classification list repeated some rows and skipped others when paged (issue #108): Trapper does not order
  it. `where()`/`all()`/`get_all()` of `classification_results` read it in pages of 500 (one request when it fits);
  a longer list drops the repeated rows and emits the new `UnstableOrderWarning`.
- `maps` and `locations_geojson` (v1, issue #125): `UnknownFilterWarning` for the filters Trapper ignores
  (`locations_geojson.get()` built its query by hand and never warned); the filter table of `locations_geojson`.
- A non-JSON error answer (Trapper's HTML `500` page) is reported as its title plus the method and URL of the request,
  instead of the whole page in the log and in the exception (issue #123).
- `research_projects.collections` (issue #121): `date_created` is a `datetime`; `UnknownFilterWarning` (the filters are
  `status`, `owner`, `owners` and `search`); the docstring example used `client.research_projects_collections`, which
  does not exist; the docs say the list is empty unless the project is approved and the user owns it or has a role.
- `users` (issue #119): `UnknownFilterWarning` for any filter (Trapper applies none and returned every user); the
  warning says "it applies no filter" for an endpoint with none.
- `species` (issue #117): `taxon_class` and `order` of v2; `UnknownFilterWarning` (`genus=Lynx` returned every
  species); the docs say the name filters are exact and case-sensitive and that v2 has the whole taxonomy (36433).
- `sequences` (issue #115): `deployment` is sent comma-separated (a list kept only one deployment); `resources`
  without the repeats of v2; `UnknownFilterWarning` for unknown filters and for `search`, which answers `500`; the
  docs say the list is not paginated and not limited to what the user can see.
- `classifications_map` (issue #113): it is the final classification list, unpaginated and with a light row (the
  docs said "resources pending classification"); the filters of the classification list (`UnknownFilterWarning`,
  `approved` sent as `status` on v1, `ValueError` for `deployment`/`collection` without `project`).
- `UnknownFilterWarning` points at the caller's line again, not at a line of the SDK, whatever the number of SDK
  functions in between (issue #113).
- `classification_package` (issue #111): `keywords`, `licenses` and `private_species` raise a `ValueError` (Trapper
  reads one text per parameter and always answered `400`); the docs said `filter_deployments` takes PKs (it is a text
  contained in `deploymentID`), now also `export_filetype="parquet"` and `split_custom_attrs` (v2); the errors for a v1
  project with no admin and for two cached packages say what to do; `UnknownFilterWarning` for unknown parameters.
- `classification_results_agg` (issue #109): typed rows (`count`, `days`, `trapRate`, coordinates and dates were
  text; the 29 columns are declared); `get_project_results_agg(geojson=True)` returned a meaningless row and is a
  `ValueError` now — new `get_project_geojson()`; no rows instead of a `400 "Empty queryset"`; the filters of the
  results table (`UnknownFilterWarning`, `approved` sent as `status` on v1, a warning for `classified` on v2, which
  answers `500`); `export_project_results_agg(raw=True)`. The guide says what a row is (a deployment and species) and
  documents `count_var`, `all_dep` and `filter_dep`.
- `user_classifications` and `ai_classifications` (issue #105): `UnknownFilterWarning` for the filters each Trapper
  version ignores (the v1 AI list ignores `rdate_*`, `user`, `sex`, ...; the v1 user list `sex`, `age`, `classified`);
  `deployment`/`collection` without `project` raise a `ValueError` (Trapper answered a `404`/`400` that read as if the
  deployment did not exist), the same check as `classification_results`; `ai_classifications.export(approved=...)`
  warns on v2, whose AI table answers `500` to it. Docstrings and guides list the filters of each version.
- `client.ai_classifications` on Trapper v2 and its `export()` on v1 and v2 (issue #104). The v2 list raised
  `ValidationError` (no `owner`, `classification` or `created_at`; attributes as `{"value", "confidence"}`): those
  fields are optional and the confidence is a fraction (`"0.93"`) on both versions, the scale of the `confidence`
  filter. `export()` raised `ValidationError` on both versions (an empty `eventID` turned into `None`; v2's flat
  boxes): its rows are now the results-table rows of `classification_results` (`AIClassificationRecordExport*`
  subclass them), a project with no AI classifications gives `[]` or an empty file instead of a `400`, and there
  is `raw=True`.
- `camtrapdp=True` gave Trapper's format in `classification_results.get_project_results()` and friends, and in
  `ai_classifications.export()` (issue #104): Trapper compares it with the text `"True"` and the SDK sent `true`.
  It is sent as `"True"`/`"False"` now (a boolean or the text `true`/`false`; anything else is a `ValueError`), with
  the same code as the booleans of the media table.
- A missing species in `user_classifications` and `ai_classifications` is `None`, not the text `"None"`
  (issue #104). Their schemas also read the v2 fields `is_setup`, `is_feedback`, `bboxes` and
  `classification_project`.
- **Behaviour change:** `private_human`, `private_vehicle`, `trapper_url` and `trapper_url_token` of the media table
  (issue #85). Trapper reads only the text `True` as true, and a Python `True` is sent as `true`, so `private_human=True`
  used to show the files of the humans (the opposite of what it says). They are now sent as `True`/`False`, so a boolean
  does what it says; a boolean or the text `true`/`false` is accepted, and anything else is a `ValueError`. Code that
  passed `True` expecting the humans to be shown now needs `False`.
- A results row of Trapper v2 with a bounding box (`[x, y, w, h]`) was read as the CamtrapDP class, with `bboxes` as text and no
  error (issue #85). `ClassificationResultRecordTrapper` reads the box of v2 as well as the list of boxes of v1, and the row
  class is chosen by the `_id` column (only the Trapper format has it), so a row it cannot read is a `ValidationError`.
- `classification_media.download_media_file()` (issue #73) read the whole file into memory, retried on any exception
  (a `404` included) and left a half-written file under its final name if the download was cut. It streams to a
  `.part` file that is moved into place when complete, retries only network errors and `502`/`503`/`504`, and sends
  nothing but the URL (no API token). Its signature is the same.
- `DeploymentExport` left `session`, `array`, `tags` and `bait_type` always empty (issue #43): Trapper has no
  column for them, it puts them in `deploymentGroups` and `deploymentTags` (with `baitType:<value>` among the
  tags). They are read from there now, and `camera_depth` is a field.
- A client that had imported locations or deployments (session login) could no longer call any
  token-authenticated POST, such as `import_classifications()`: the web session's cookies were sent
  with every REST call and Trapper answered `403 CSRF Failed`. Session and token requests now use
  separate HTTP clients.
- `resources.get_by_location()` / `find_by_location()` raised `ValidationError`: the
  `/storage/api/resources/location/<pk>` endpoint omits `name`, which `Resource` required. It is now optional.
- `locations_geojson.get()` returned the `{pagination, results}` envelope instead of the documented
  `FeatureCollection`.
- `classification_results.where_project_results()` (and any other `where()` whose schema is a
  `Union`, such as `ClassificationRecordExport`) failed on the first page with
  `AttributeError: model_validate`: `APIQuery` called `model_validate`/`model_construct` on the
  schema directly. It now parses rows the same way `get()` already did — through a `TypeAdapter`
  for a `Union` or `Annotated` schema (always validated, as only validation can pick the member).
- `deployments.by_collection()`/`export_by_collection()` returned every deployment on the server,
  whichever collection was asked for: they sent a `colls` filter Trapper's deployment API doesn't
  have (it silently ignores unknown parameters). They now check each candidate deployment
  against the resource API, which does filter by collection and deployment — pass the usual
  filters (e.g. `research_project=...`) to narrow the candidates. `by_collection()` now returns a
  `list` instead of a lazy `APIQuery`. The docs also no longer list `collections` as a
  deployment filter.
- `classification_package.get_project_package()` no longer surfaces a raw stringified
  `{'data': {...}}` dict as the error message on a failed request (e.g. a package generation
  failure returned as a 400) — it now extracts the server's actual `data.message`/`data.errors`,
  matching the fix already applied to `import_classifications()`. Also no longer crashes with a
  raw `JSONDecodeError` on a non-JSON (HTML) error page from a genuine unhandled server-side
  exception.

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

