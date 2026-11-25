# Trapper API: proposed issues

Draft issues for the Trapper project, found while building `wildintel-trapper-sdk`. Each one is
written to be copied to the tracker as it is: title, what happens today, what is proposed, and what
the SDK does in the meantime.

- **Tracked in** [#26](https://github.com/wildintelproject/wildintelproject-trapper-sdk/issues/26), an issue
  that stays open: Trapper's API is not ours, so nothing here is "fixed" by a pull request of this repository.
- **Checked against:** the Trapper v1 source (`development`, v1.7.3-63) and a live v1.7.4 server.
- **Trapper v2:** not checked unless an issue says so. Re-check each one before filing it.
- Add new issues at the end, keep the numbering, and move one to the *Done* list when Trapper fixes it.
  Mark what was not checked as *(unverified)*, and open the pull request with `Refs #26`, not `Closes`.

| # | Title | Area |
|---|---|---|
| 1 | Add an endpoint to create research projects | research |
| 2 | Add update and delete endpoints for research projects | research |
| 3 | Return every research project field from the API | research |
| 4 | Let owners see their own pending research projects | research |
| 5 | Answer rejected create/update requests with a JSON `400` | cross-cutting |
| 6 | Manage research project roles and collections through the API | research |
| 7 | Add create endpoints for classification projects and classificators | media_classification |
| 8 | Import locations and deployments through the API | geomap |
| 9 | Expose the outcome of asynchronous imports | cross-cutting |
| 10 | Answer an invalid classification import with a `400` and the report | media_classification |
| 11 | Reject a blank `timezone` and `research_project` on import | geomap |
| 12 | Accept token authentication for every write operation | cross-cutting |
| 13 | Do not delete on a `GET` request | media_classification |
| 14 | Return primary keys, not names, for the related objects of a classification project | media_classification |
| 15 | Return the species and standard attributes of a classificator | media_classification |
| 16 | Reject unknown species when saving a classificator | media_classification |
| 17 | Approve or reject a pending research project through the API | research |
| 18 | Filter research projects by name, status and keyword, and reject unknown filters | research |
| 19 | Expose the valid values of the research project choice fields | research |
| 20 | Return the primary keys of the owner and the members of a research project | research |
| 21 | Use one URL convention, and answer API paths with JSON | cross-cutting |
| 22 | Create, update and delete locations through the API | geomap |
| 23 | Return every field of a location, and its related objects as keys | geomap |
| 24 | Return the coordinates of a location as numbers | geomap |
| 25 | Filter the list of locations by area | geomap |
| 26 | Reject the filters and the ordering the list does not apply | cross-cutting |
| 27 | Create, update and delete deployments through the API | geomap |
| 28 | Return every field of a deployment, and its related objects as keys | geomap |
| 29 | Give `session`, `array` and the bait type their own columns in the deployment export | geomap |
| 30 | Write the dates of a deployment in one format | geomap |
| 31 | Answer an empty export with an empty CSV, not a `400` | cross-cutting |
| 32 | Filter the list of deployments by collection | geomap |
| 33 | Filter the list of deployments by area in every version | geomap |
| 34 | Create, update and delete resources through the API | storage |
| 35 | Return every field of a resource, and its related objects as keys | storage |
| 36 | Serve the files of a resource with the API token | storage |
| 37 | Do not answer `deployment__isnull` with a `500` | storage |
| 38 | Read every list filter of a resource the same way | storage |
| 39 | Do not turn every model field of a resource into a filter | storage |
| 40 | Add an export endpoint for resources | storage |
| 41 | Download a set of resources through the API, asynchronously and by filters | storage |
| 42 | Create, update and delete collections, and add or remove their resources, through the API | storage |
| 43 | Return every field of a collection, and how many resources it has | storage |
| 44 | Give the collection endpoints one shape | storage |
| 45 | Reject a collection `status` that does not exist | storage |
| 46 | Create a collection from a package through the API, and follow the task | storage |
| 47 | Read the boolean parameters of the media table as booleans | media_classification |
| 48 | Answer an empty media or results table with an empty list, not a `400` | media_classification |
| 49 | Let the media table be read in pages | media_classification |
| 50 | Say in the media table what each image shows, and fill `exifData` | media_classification |
| 51 | Filter by the collection's own pk, not by its link to the classification project | media_classification |
| 52 | Make `private_species` of the media table work | media_classification |
| 53 | Create, update and approve classifications through the API | media_classification |
| 54 | Return in the classification list the fields the results table has | media_classification |
| 55 | Document the format of the results table that can be imported, and what `observationID` is | media_classification |
| 56 | Use one shape for `bboxes` in both versions, and do not fail the whole results table for one row | media_classification |
| 57 | Do not fetch the Camtrap DP schema from the internet in every classification import | media_classification |
| 58 | Answer `classified` and `classified_ai` in the results and media tables | media_classification |
| 59 | Call the filter for an approved classification the same in v1 and v2 | media_classification |
| 60 | Make `approved` work in the AI results table of v2 | media_classification |
| 61 | Return the same fields in the AI classification list of v1 and v2 | media_classification |
| 62 | Use one scale for the confidence of an AI classification | media_classification |
| 63 | Filter the user and AI lists by deployment or collection without the project | media_classification |
| 64 | Apply the same filters to the user and AI lists in v1 and v2 | media_classification |
| 65 | Read `camtrapdp` (and every boolean) as a boolean, and say "no species" with `null` | cross-cutting |
| 66 | Read the list parameters of the data package (`keywords`, `licenses`, `private_species`) | media_classification |
| 67 | Make `release` and `get_released` of the data package work, and never cache two packages for one key | media_classification |
| 68 | Do not fail the data package of a project with no admin | media_classification |
| 69 | Limit the sequences to what the user can see, and fix their `search` | media_classification |
| 70 | Do not show every account and its email to every user, and let the user list be filtered | accounts |

---

## 1. Add an endpoint to create research projects

**Labels:** enhancement, api

**Problem.** `ResearchProjectViewSet` is a `PaginatedReadOnlyModelViewSet`. A research project can
only be created through the web form `research/project/create/`, so a script or integration cannot
create one.

**Proposal.** `POST research/api/projects`, authenticated with a token, answering `201` with the
project as `GET research/api/projects/<pk>` shows it. As in the form, the authenticated user
becomes the owner and a project administrator, and a non-staff user's project stays *not approved*
until an administrator approves it.

Fields: `name`, `acronym` (3 to 10 characters; both unique), `sampling_design`, `sensor_method`,
`animal_types`, `bait_use`, `event_interval`, `keywords`, `abstract`, `methods`, `description`, and
`project_roles`. `keywords` is a **list**: the web form takes a single string, and Trapper parses it
with django-taggit, which splits on spaces when there is no comma, so one keyword with a space
(`camera trap`) is saved as two (`camera` and `trap`) unless it is quoted. A list has no such trap.

**Members in the same request.** The web form takes the project's members together with the project
(a `project_roles` formset). Checked against a v1.7.4 server: it accepts any number of rows, each with
a user and a role (`1` admin, `2` expert, `3` collaborator); it refuses the same user twice with
`This user already has a role in this project.`; and it does not require the creator to be one of the
members, nor any member at all. The endpoint should take the same list, so that a project and its team
are created in one call, and answer `400` for a repeated user:

```json
{"name": "Doñana mammals", "acronym": "DONMAM",
 "project_roles": [{"user": 7, "name": "expert"}, {"user": 9, "name": "collaborator"}]}
```

**Workaround in the SDK.** `research_projects.create()` simulates the form with a cookie session and
a CSRF token. It needs `user_name`/`user_password` (the *email* on servers that log in by email), so
a token alone cannot create a project. Members can be sent with it, but only when the project is
created: there is no way to change them afterwards (see #6).

## 2. Add update and delete endpoints for research projects

**Labels:** enhancement, api

**Problem.** `research/project/update/<pk>/` and `research/project/delete/<pk>/` are web views only.
The serializer already tells the client whether the user may use them (`update_data`,
`delete_data`), but there is no API call to use them with.

**Proposal.** `PATCH`/`PUT`/`DELETE research/api/projects/<pk>`, honouring the existing role
permissions (administrators only).

**Workaround in the SDK.** None: the SDK cannot update or delete a research project.

## 3. Return every research project field from the API

**Labels:** enhancement, api

**Problem.** `ResearchProjectSerializer.Meta.fields` is a hand-written list that stops at what the
web grid needs. These model fields are stored but never returned: `sampling_design`,
`sensor_method`, `animal_types`, `bait_use`, `event_interval`, `abstract`, `methods`, `description`
and `is_citizen_science`. Today's output has only `pk`, `name`, `owner`, `owner_profile`, `acronym`,
`keywords`, `date_created`, `project_roles`, `update_data`, `detail_data`, `delete_data` and `status`.

**Proposal.** Return them, with each choice field as its value and its label. Keep the grid-oriented
fields (`update_data`, ...) so nothing existing breaks.

**Workaround in the SDK.** None. A project created with those values cannot be read back through
the API (only on the web page of the project).

## 4. Let owners see their own pending research projects

**Labels:** bug, api

**Problem.** `ResearchProject.objects.get_accessible()` ends in `.filter(status=True)`, so it hides
every project that is not approved, even from its owner. A non-staff account creates its project
with `status=None` (waiting for an administrator) and then cannot find it through the API.

**Proposal.** Include, for the owner and the project's administrators, the projects that are not yet
approved, and return their `status` so a client can tell them apart.

**Workaround in the SDK.** `research_projects.create()` returns `None` when the new project cannot
be read back.

## 5. Answer rejected create/update requests with a JSON `400`

**Labels:** enhancement, api

**Problem.** The web forms answer an invalid submission with `200` and the form re-rendered as HTML.
The reason is inside the markup (for a research project, `name: Research project with this Name
already exists.` in a `help-block`; the page banner only says "Error creating new project").

**Proposal.** In the API endpoints from #1, #2, #6, #7, #8 answer `400` with the errors by field:

```json
{"name": ["Research project with this Name already exists."], "acronym": ["Ensure this value has at least 3 characters (it has 2)."]}
```

**Workaround in the SDK.** `APIClientBase._extract_html_error_text()` scrapes the `help-block`
markup. It breaks when the template changes.

## 6. Manage research project roles and collections through the API

**Labels:** enhancement, api

**Problem.** Granting a role on a project, and linking or unlinking collections
(`project/collection/add/` and its delete views), only exist as web forms. The API reads both
(`project_roles`, `research/api/project/<pk>/collections`) but cannot change them.

**Proposal.** Endpoints to add, change and remove the roles of a project, and to link or unlink a
collection (`POST`/`DELETE research/api/project/<pk>/collections`).

**Workaround in the SDK.** None.

## 7. Add create endpoints for classification projects and classificators

**Labels:** enhancement, api

**Problem.** `ClassificationProjectViewSet`, `ClassificationProjectCollectionViewSet` and
`ClassificatorViewSet` are all read-only. Creating a classification project (`project/create/`),
linking a collection to it (`project/collection/add/`) and creating a classificator
(`classificator/create/`) are web forms.

**Proposal.** `POST media_classification/api/projects`, `POST .../project/<pk>/collections` and
`POST media_classification/api/classificators`, answering `201`. A classificator is a taxonomy and
attribute schema, so its JSON representation (species, tracked species, the dynamic attributes and
the form template) needs agreeing first.

**Notes.** Adding collections to a classification project (`project/collection/add/`) takes the primary
keys of the *research project's* collection links (`ResearchProjectCollection`), not of the storage
collections, and the collections must already be linked to the research project. An API should take
the storage collection primary keys and say clearly when one is not part of the research project.

**Workaround in the SDK.** `classification_projects.create()`, `.add_collections()` and
`.remove_collection()` and `classificators.create()` simulate the forms.

## 8. Import locations and deployments through the API

**Labels:** enhancement, api

**Problem.** The REST API is read-only for locations and deployments. They can be imported only
through the web import forms (`geomap/location/import/`, `geomap/deployment/import/`), which need a
cookie session and a CSRF token. On Trapper v2 they became Django-admin actions that need a staff
account.

**Proposal.** `POST geomap/api/locations/import/` and `POST geomap/api/deployments/import/`, with
token authentication, taking the same CSV (and GPX for locations) and fields as the forms, and
answering `202` with something to follow the import by (see #9).

**Workaround in the SDK.** `locations.import_locations()` and `deployments.import_deployments()`
simulate the forms.

## 9. Expose the outcome of asynchronous imports

**Labels:** enhancement, api

**Problem.** Locations and deployments are imported by a celery task, and there is no endpoint to
ask whether it finished or failed. A failure is only visible in the task result table, and the
request that queued it has already answered success.

**Proposal.** Return a task id when the import is queued and offer `GET .../tasks/<id>/` with
`state`, `progress` and the per-row errors when it fails.

**Workaround in the SDK.** `wait_for_import()` polls the list API until the imported rows appear,
and gives up after a timeout. It cannot tell a failed import from a slow one.

## 10. Answer an invalid classification import with a `400` and the report

**Labels:** bug, api

**Problem.** `POST media_classification/api/classifications/import/` answers a bare HTTP `500` when
the table fails validation: Trapper cannot serialize its own validation report. Seen on v1 and v2.

**Proposal.** Answer `400` with the validation report (the failing rows and why).

**Workaround in the SDK.** `import_classifications(check_table=True)` checks the table locally
first (`_id` and `classificationMethod` columns, `sex` only `female`/`male`), and the `APIError`
for a `500` lists what to check.

## 11. Reject a blank `timezone` and `research_project` on import

**Labels:** bug, geomap

**Problem.** `LocationImportForm` declares `timezone` and `research_project` with
`required=False`. A missing `research_project` is rejected later by `clean_research_project()` with
a `200` that looks like success. A blank `timezone` is not rejected at all: the rows are saved with
`bulk_create()`, which skips model validation, and the corrupt value breaks later listings with a
`500`, long after the import reported success.

**Proposal.** Declare both fields as required in the form, and validate the rows before
`bulk_create()`.

**Workaround in the SDK.** `import_locations()` makes both arguments mandatory.

## 12. Accept token authentication for every write operation

**Labels:** enhancement, api

**Problem.** Everything that is a web form (#1 to #8) needs `user_name`/`user_password`, and on
servers that log in by email the user name has to be the email address. An integration cannot hold
only a token.

**Proposal.** Give each write operation an API endpoint (the issues above), so that a token is
enough.

**Workaround in the SDK.** `session_login()` and `session_post_multipart()`.

## 13. Do not delete on a `GET` request

**Labels:** bug, security

**Problem.** `BaseDeleteView` deletes the object on `GET` (`project/collection/delete/<pk>/`,
`project/delete/<pk>/`, and every view built on it). A `GET` that changes data can be triggered by a
link, an image tag or a prefetch, and is not protected by the CSRF token the `POST` variant carries.
Deleting a project collection also deletes the classifications made on it (`on_delete=CASCADE`).

**Proposal.** Delete only on `DELETE` (or `POST`) and answer `204`, with the reason in the body when it
is refused (no permission, protected objects) instead of a redirect with a flash message.

**Workaround in the SDK.** `remove_collection()` issues the `GET` and then checks through the API
that the link is gone.

## 14. Return primary keys, not names, for the related objects of a classification project

**Labels:** enhancement, api

**Problem.** `GET media_classification/api/projects/` returns `classificator` as a primary key but
`research_project` as the research project's *name*. A client cannot tell which research project it is
without a second lookup by name, and the add-collections form needs the primary key.

**Proposal.** Return both as primary keys (plus the name next to it if it is wanted, e.g.
`research_project` and `research_project_name`).

**Workaround in the SDK.** The research project's primary key is looked up by its name, which is
unique.

## 15. Return the species and standard attributes of a classificator

**Labels:** enhancement, api

**Problem.** `GET media_classification/api/classificators/` returns the name, the owner, the
`predefined_attrs`/`custom_attrs` and the attribute order, but not what the creation form asks for:
`species`, `tracked_species`, `template` and the standard flags (`sex`, `age`, `count_new`,
`behaviour`, `individual_id`, `classification_confidence`). They can be set and not read back.

**Proposal.** Return them. The attribute order only lists the enabled optional attributes, so the
flags can be guessed from it, but the species and the template cannot.

**Workaround in the SDK.** None.

## 16. Reject unknown species when saving a classificator

**Labels:** bug, media_classification

**Problem.** `ClassificatorForm.clean()` turns the comma-separated species into
`Species.objects.filter(pk__in=...)`. A primary key that does not exist is dropped without an error, so a
classificator whose `species` are all unknown is saved with an empty list, which means *every species
is valid*.

**Proposal.** Compare the number of species found with the number asked for, and fail with the
unknown keys. Same for `tracked_species`.

**Workaround in the SDK.** None: the docs ask the user to check the keys with `client.species`.

## 17. Approve or reject a pending research project through the API

**Labels:** enhancement, api

**Problem.** A project created by a non-staff account stays *not approved* (`status=None`) until an
administrator approves it, and that is only possible in the Django admin: the field is read by the API
and set nowhere else (the creation view sets it to approved for staff, and nothing else touches it). The
administrators are notified by e-mail with a link to the admin.

**Proposal.** An action for administrators, for example `POST research/api/projects/<pk>/approve` and
`.../reject`, or `status` as a writable field of the `PATCH` in #2. Approving already sends the
notification to the owner (a signal on the status change), so nothing else has to change.

**Workaround in the SDK.** None: an integration that creates projects for non-staff accounts cannot
finish the job.

## 18. Filter research projects by name, status and keyword, and reject unknown filters

**Labels:** enhancement, api

**Problem.** `ResearchProjectFilter` accepts `owner`, `keywords` and `acronym`; search covers name,
acronym, abstract and owner but is a partial match. Checked against a v1.7.4 server:

- `name` and `status` are **not** filters, and are **ignored silently**: `?name=zzz` and `?status=false`
  return the same 20 projects as no filter at all. A client that mistypes a filter name gets everything.
- `keywords` filters by the primary key of the tag, but no endpoint lists the keywords, so a client
  cannot know the key. An unknown key answers `400`, as it should.

The same happens on the other endpoints: `GET geomap/api/locations?unknown_filter=1` returns all 16 locations
of the test server, as no filter would.

**Proposal.** Add `name` (exact) and `status` filters; accept keywords by name (`?keywords=mammals`) or
add a keywords endpoint; and answer `400` for a query parameter the endpoint does not know, as it does
for a bad `keywords` value.

**Workaround in the SDK.** `search=` and a comparison of the name in the client.

## 19. Expose the valid values of the research project choice fields

**Labels:** enhancement, api

**Problem.** `sampling_design`, `sensor_method`, `animal_types` and `bait_use` accept a closed list of
values, but nothing in the API lists them: there is no endpoint, and `OPTIONS research/api/projects`
returns only the name, description and parsers (the viewset is read-only, so it has no field
metadata). Clients copy the lists from Trapper's source code and can fall behind.

**Proposal.** Once the endpoint of #1 exists, `OPTIONS` on it would describe the fields with their
choices, which is what Django REST Framework does by default for a writable serializer. Until then, a
read-only listing would do.

**Workaround in the SDK.** The values are copied into `trapper_client.enums`.

## 20. Return the primary keys of the owner and the members of a research project

**Labels:** enhancement, api

**Problem.** `GET research/api/projects` returns the owner as a display name (`"owner": "rp_staff"`) and a
profile URL, and each entry of `project_roles` as `user` (a display name), `username`, `profile` (a URL)
and `roles` (labels, as in `["Admin"]`). Checked against a v1.7.4 server: no primary key of a user, and no
numeric value of a role. A client cannot tell which user of `accounts/api/users` is the owner or a member
without matching names, and cannot compare a role with the values the form accepts (`1`, `2`, `3`).

**Proposal.** Return the owner and every member with their primary key (`owner` as an object, or an
`owner_id` next to the name), and each role as its value and its label, as proposed for the choice fields
in #3. This is what the create and roles endpoints of #1 and #6 would take.

**Workaround in the SDK.** Members are matched by user name.

## 21. Use one URL convention, and answer API paths with JSON

**Labels:** bug, api

**Problem.** The API mixes two conventions. Checked against a v1.7.4 server:

- `research/api/projects`, `research/api/projects/3`, `media_classification/api/projects` and
  `media_classification/api/classificators` answer `200`, while the same paths with a trailing slash
  answer `404`.
- `geomap/api/locations/geojson/` answers `200` and without the slash it answers `404`.
- A path that is not found under `/api/` answers an **HTML** page (`404 text/html`) for some routes and JSON
  for others.

A client has to know which convention each route uses, and cannot read the error of a wrong one.

**Proposal.** One convention for every route (the router's own is no trailing slash), accepting the other
with a redirect, and a JSON body for every error under the API, including `404`.

**Workaround in the SDK.** Each component spells its endpoint the way the server expects it.

## 22. Create, update and delete locations through the API

**Labels:** enhancement, api

**Problem.** `LocationViewSet` is a `PaginatedReadOnlyModelViewSet`: `OPTIONS geomap/api/locations` answers
`Allow: GET, HEAD, OPTIONS`. A location can only be created in bulk, by the CSV import form (#8), and can
only be edited or deleted in the web map (`update_data` points to `/geomap/map/?locations=16&edit=true`).
The import creates locations; it does not update the ones that exist: it only reads `locationID`, `longitude`,
`latitude` and a few optional columns, ignores `_id`, and rejects a `locationID` that exists in the research
project. The **deployment** import does update, with its `update` option and an `_id` column (*checked in the
source, v1*), so the two imports behave differently.

**Proposal.** `POST geomap/api/locations`, and `PATCH`/`PUT`/`DELETE geomap/api/locations/<pk>`, with token
authentication and the permissions the web views already check (owner and managers). Fields: `location_id`,
`name`, `description`, `coordinates`, `timezone`, `ignore_DST`, `coordinate_uncertainty`, `is_public` and
`research_project`. Validate the `timezone` (see #11).

**Workaround in the SDK.** `locations.import_locations()` creates locations from a CSV, one row or many. There
is no way to correct or delete one.

## 23. Return every field of a location, and its related objects as keys

**Labels:** enhancement, api

**Problem.** Checked against a v1.7.4 server, `GET geomap/api/locations` returns `city`, `coordinates`,
`country`, `county`, `date_created`, `description`, `is_public`, `location_id`, `name`, `owner`,
`owner_profile`, `pk`, `research_project`, `state`, `timezone` and the `update_data`/`delete_data` URLs. It
leaves out `ignore_DST`, `coordinate_uncertainty` and `managers`, which the model has and the CSV export
(`geomap/api/locations/export/`) partly carries (`ignoreDST`). Related objects are display values, not keys:

- `owner` is a user name (`"rp_staff"`);
- `research_project` is the **acronym** (`"c50e23d"`), while the CSV export gives its primary key (`1`) in
  `researchProject`: the same field in two shapes.

The same location comes in **three shapes**, and neither the JSON nor the export holds every field. Checked
on v1.7.4 and on a v2 server: the JSON has the name, the owner, `is_public`, `date_created` and the place names
that the export does not have; the export has `ignoreDST`, `habitat`, the research project as a key and the
coordinates as two numbers, which the JSON does not. On v2 the JSON does not even carry `city`, `county`,
`state` and `country`, while the export carries `country`.

**Cause.** In Trapper's source there is one serializer per shape, each with its own hand-written field list:
`LocationSerializer` (the JSON list and detail), `LocationGeoSerializer` (the GeoJSON, which only sends `pk`,
`location_id` and `name`) and `LocationTableSerializer` (the CSV). They are not derived from one another, so
they drift apart.

**Proposal.** Return the missing fields, and the owner and the research project as primary keys (with the
name or acronym next to them if it is wanted). Same as #14 and #20 for classification and research projects.
Make the JSON detail the complete representation of a location, and build the other two from it (or from one
shared field list) so that the same piece of data cannot change value with the format.

**Workaround in the SDK.** `locations.export(file=None)` returns `ignore_dst`, `habitat` and
`research_project_id`, so those can be read from there; the SDK does not join the two shapes. `Location`
gets `longitude` and `latitude` from the coordinates string. `coordinate_uncertainty` and `managers` are in
neither, and cannot be read.

## 24. Return the coordinates of a location as numbers

**Labels:** enhancement, api

**Problem.** The list returns `"coordinates": "-6.44, 37.05"`, a single string with the longitude first.
There is no GeoJSON or pair of numbers, and nothing says which is the axis order. The GeoJSON endpoint
(`geomap/api/locations/geojson/`) returns a proper `Point` (`[-6.44, 37.05]`), but it was removed in Trapper
v2.

**Proposal.** `longitude` and `latitude` as numbers in the list and the detail (or a GeoJSON `geometry`), in
Trapper v1 and v2.

**Workaround in the SDK.** `Location.coordinates` is the raw string; the caller splits it. The GeoJSON
endpoint is wrapped by `client.locations_geojson` (Trapper v1 only).

## 25. Filter the list of locations by area

**Labels:** enhancement, api

**Problem.** `LocationFilter` excludes `coordinates`, so the list has no complete spatial filter. Checked live:

| | `in_bbox` | `radius` |
|---|---|---|
| v1, `GET geomap/api/locations` | **ignored silently** (`0,0,1,1` returns 16 of 16) | **ignored silently** |
| v2, `GET geomap/api/locations` | applied, edges included (`-7,36,-5,38` returns 13 of 15) | **ignored silently** |
| v1, GeoJSON endpoint | applied | applied |

The only endpoint that applies `radius` is the GeoJSON one, which Trapper v2 removed.

**Proposal.** Apply `in_bbox` and `radius` on the list in every version, and keep them when the GeoJSON endpoint
goes.

**Workaround in the SDK.** `client.locations.in_area(bbox=..., center=..., radius=...)` filters on the client, in
both versions (on v2 it also sends the box as `in_bbox`, to read fewer pages), and the SDK warns when a filter
the list does not apply is passed (see entry 26). `client.locations_geojson.get(in_bbox=..., radius=...)` still works
on Trapper v1.

## 26. Reject the filters and the ordering the list does not apply

**Labels:** enhancement, api, cross-cutting

**Problem.** The list endpoints answer `200` with **every** item when a query parameter is not a filter they
know, so a typo or a filter that exists only in the other version looks like a success. Checked live on the
locations list in v1 and v2: `?foo=bar`, `?ignoreDST=true`, `?radius=0,0,1` and `?country=ZZ` on v2 change
nothing. `?ordering=-name` and `?ordering=bogus` also change nothing: the list is not orderable, and says
nothing. (A filter with an invalid value is answered with a `400` and the field, as it should.)

**Proposal.** Answer `400` with the names of the unknown parameters, or at least list the accepted filters in the
`OPTIONS` response, and either implement `ordering` or reject it.

**Workaround in the SDK.** For locations and deployments, `UnknownFilterWarning` names the filters the server would
ignore; the filters each version applies are listed in their guides (checked live on v1 and v2: `colls`,
`collections`, `ordering`, `radius`, `bait_use` and a typo are ignored on the deployment list too), and for
resources (`ordering`, `in_bbox`, `radius` and a typo; `locations_map` on v2) and collections (`ordering`, `description`,
`date_created`, a typo; `locations_map` on v2). The media table of a classification project (and the classification list and results) are described in #47 to #51; the other endpoints are not checked yet.

## 27. Create, update and delete deployments through the API

**Labels:** enhancement, api

**Problem.** `DeploymentViewSet` is a read-only viewset: `OPTIONS geomap/api/deployments` and
`geomap/api/deployments/<pk>` answer `Allow: GET, HEAD, OPTIONS` on v1 and v2. A deployment can be created in
bulk by the CSV import form (#8), and created, edited or deleted one by one only in the web views
(`geomap/deployment/create|update|delete/<pk>/`). The import is the one way to **update** by script: with its
`update` option and an `_id` column it changes the deployments that exist (checked on v1 and v2: export, edit,
import, and the value changes). Two things make that fragile:

- It answers `True` before the change is applied, and nothing says when it has been (#9): a read just after still
  gives the old value.
- A number that is `0` is stored as `NULL`: importing `cameraHeight=0` as an update leaves the height empty
  (checked on v1 and v2), because the importer skips every falsy value (`if val:`).

**Proposal.** `POST geomap/api/deployments`, and `PATCH`/`PUT`/`DELETE geomap/api/deployments/<pk>`, with token
authentication and the permissions the web views already check, and a way to know when an import has finished
(#9). Apply an explicit `0` and an empty text as such.

**Workaround in the SDK.** `deployments.import_deployments(update=True)` with the CSV that
`deployments.export(raw=True)` gives (it keeps `_id`), and `deployments.wait_for_update()` to know when the new
values are there. There is no way to create or delete a single deployment, and a `0` cannot be written.

## 28. Return every field of a deployment, and its related objects as keys

**Labels:** enhancement, api

**Problem.** Checked on v1 and v2, a deployment has two shapes and neither is complete. `GET
geomap/api/deployments` gives `pk`, `deployment_code`, `deployment_id`, `location`, `location_id`, `start_date`,
`end_date`, `owner`, `owner_profile`, `research_project`, `tags`, `correct_setup`, `correct_tstamp` and three
action URLs. `geomap/api/deployments/export/` gives 25 columns, among them the camera fields, `habitat`,
`deploymentComments`, `latitude` and `longitude`, but **not** the owner, the research project, `correct_setup`
or `correct_tstamp`. From the model, `view_quality`, `date_created`, `managers`, `capture_method`,
`is_incomplete` and `status` are in neither *(unverified on a server)*. As with locations (#23), each shape is
built by its own serializer. Besides:

- The related objects come in different forms in the same row: `location` is a primary key, `location_id` the
  text key of that location, `research_project` an **acronym** and `owner` a **user name**, and the export has
  none of the three.
- The same flag has opposite meanings: `correct_tstamp` is `true` when the timestamps are right, and the export
  column `timestampIssues` is `true` when there are problems. The export negates it and the import negates it
  back (checked: importing `timestampIssues=true` sets `correct_tstamp` to `false`).
- The list has fields made for the web page: `detail_data`, `update_data`, `delete_data` and `owner_profile` are
  URLs of the web views on v1 and `null` on v2.

**Proposal.** One serializer for the whole deployment, with the related objects as primary keys (and a name next
to them if it helps), and the others (CSV, GeoJSON) built from it. Name the timestamp flag the same way in
both. Leave the web-page fields out of the API.

**Workaround in the SDK.** The guide lists the fields of each shape and gives the join by `pk` that gets all of
them; the fields that are in neither cannot be read.

## 29. Give `session`, `array` and the bait type their own columns in the deployment export

**Labels:** enhancement, api

**Problem.** The export has no `session`, `array` or `baitType` column. `DeploymentsSerializer` packs the first two
into `deploymentGroups` (`session:S | array:A`) and the tags into `deploymentTags`, joined by ` | `, and
**appends** the bait type to those tags as `baitType:<value>`, so a bait looks like a tag. Checked on v2 with a
deployment imported with `session:s1 | array:a1` and `spring | x`: the export gives those two columns as they went
in. The importer reads `deploymentGroups` and `deploymentTags` back, but has no `baitType` column, so a bait
cannot be set by import and the packed form was read from the source only *(unverified on a server)*. `baitUse` is
derived from the bait type.

**Proposal.** Real `session`, `array` and `baitType` columns, accepted by the import too, and the tags alone in
`deploymentTags`.

**Workaround in the SDK.** `DeploymentExport` splits them: `session`, `array`, `tags` and `bait_type`.

## 30. Write the dates of a deployment in one format

**Labels:** enhancement, api

**Problem.** The same instant is written in two ways. Checked on v1 and v2: the JSON list gives
`2024-01-01T00:00:00+01:00` and the export `2024-01-01T00:00:00+0100`, without the colon in the offset. The
timezone name is in neither shape (the offset comes from the deployment's own timezone, `start_date_tz`, in the
source *(not checked with a deployment in another timezone)*).

**Proposal.** ISO 8601 with the colon in the offset in both, and the timezone name as a field.

**Workaround in the SDK.** The dates of `Deployment` and `DeploymentExport` are read as timezone-aware `datetime`.

## 31. Answer an empty export with an empty CSV, not a `400`

**Labels:** bug, api, cross-cutting

**Problem.** `GET geomap/api/deployments/export/` and `geomap/api/locations/export/` answer `400
["Empty queryset or you have no permission to access the requested objects."]` when no row matches (checked on v1
and v2), while the list with the same filter answers `200` with `count: 0`. A filter that matches nothing and a
missing permission look the same, and a caller must treat a `400` as a normal result.

**Proposal.** Answer `200` with the header row only, and `403` for a missing permission.

**Workaround in the SDK.** The guide warns about the `BadRequestError`, and `deployments.wait_for_update()`
counts it as "not there yet".

## 32. Filter the list of deployments by collection

**Labels:** enhancement, api

**Problem.** The list of deployments has no collection filter in the servers checked (v1.7.4 and a v2 build):
`?collections=2`, `?collection=2` and `?colls=2` are ignored and every deployment comes back, although a
deployment's media belong to collections. The development source (`v1.7.3-63`) declares a `collections` filter
(`CollectionDeploymentFilter`) in `DeploymentFilter` that the servers tested do not have, and it was **not** tried
*(unverified)*.

**Proposal.** Ship that filter and apply it to the list and to the export.

**Workaround in the SDK.** `deployments.by_collection()`, `by_collection_with_counts()` and
`export_by_collection()` ask the resources API, one request per candidate deployment.

## 33. Filter the list of deployments by area in every version

**Labels:** enhancement, api

**Problem.** A deployment has no coordinates in the JSON, only its location's pk. The list applies `in_bbox` on
v2 (`-7,36,-5,38` returns 13 of 15) and **ignores it on v1** (the same request returns every deployment); `radius`
is ignored by both. The export has `latitude` and `longitude` but no spatial filter on v1.

**Proposal.** Accept `in_bbox` and `radius` on the list and the export in every version (see #25 for locations).

**Workaround in the SDK.** `deployments.in_area()` finds the locations in the area and asks for their
deployments; the SDK warns when a filter the list does not apply is passed (see entry 26).

## 34. Create, update and delete resources through the API

**Labels:** enhancement, api

**Problem.** `ResourceViewSet` is a read-only viewset: `OPTIONS storage/api/resources` answers `Allow: GET, HEAD,
OPTIONS` on v1 and v2. A resource is created by an upload (its own endpoints and the uploader), and can only be
edited or deleted in the web views: the list gives their URLs in `update_data` and `delete_data` (v1; `null` on v2).
There is no way to correct the name, the tags or the date of a resource by script, or to delete one.

**Proposal.** `PATCH`/`PUT`/`DELETE storage/api/resources/<pk>`, with token authentication and the permissions the
web views already check. Delete on `DELETE`, not on a `GET` (see #13).

**Workaround in the SDK.** None: resources can be read and downloaded, not changed.

## 35. Return every field of a resource, and its related objects as keys

**Labels:** enhancement, api

**Problem.** `GET storage/api/resources` gives 18 keys (checked on v1 and v2): `pk`, `name`, `owner`,
`owner_profile`, `resource_type`, `date_recorded`, `observation_type`, `species`, `tags`, `url`, `url_original`,
`mime`, `preview_url`, `thumbnail_url`, `update_data`, `detail_data`, `delete_data` and `date_recorded_correct`.
It does **not** say which deployment a resource belongs to, which collections it is in, its `status`, when it was
uploaded, or its size and checksum, although the model has them and the list can be filtered by deployment,
collection and status. The deployment only appears on `storage/api/resources/location/<pk>`, as the text
`deployment_id` (v2; that sub-endpoint also leaves out the name, the owner and the URLs), so finding the deployment
of a resource takes one request per deployment. The related objects that do come are names (`owner`, `tags`), and
`observation_type` and `species` are lists of strings *(not seen with data: no resource of the test servers is
classified)*. As with locations (#23), the keys the web page needs (`update_data`, `detail_data`, `delete_data`,
`owner_profile`) are in the API: URLs on v1 and `null` on v2.

**Proposal.** One serializer with the whole resource, the related objects as primary keys (`deployment`,
`collections`, `owner`), and the other shapes built from it. Leave the web-page fields out.

**Workaround in the SDK.** `resources.where(deployments=...)` and `where_by_collection()` go the other way: from a
deployment or a collection to its resources. The deployment of one resource cannot be read.

## 36. Serve the files of a resource with the API token

**Labels:** enhancement, api

**Problem.** The resources API lists resources but does not serve their files. They come from a web view,
`storage/resource/media/<pk>/file/` (and `pfile`, `tfile`), which does not take the API token: with a token, or with no
login at all, it answers `404`, and it answers `404` too when the account has no permission (the view raises `Http404`
instead of `403`), so a missing file and a forbidden one look alike. With a web session it serves the file (checked on
v1 and v2: the original JPEG). `url` is the preview, which does not exist if it was not generated (`404`), and
`preview_url` and `thumbnail_url` fall back to a placeholder that is a static file. Behind no proxy, a development v1
answers `200` with an empty body and an `X-Accel-Redirect` header.

There is a way in without a session, but it is not in the resources API. The view accepts the resource's own token as
`?rt=<token>`, and **the media table of a classification project** (`GET media_classification/api/media/<project_pk>/`)
gives it in the URL of every file: an anonymous `GET` of that URL answers `200` with the file (checked on v1 and v2).
So the token exists and works, but:

- it is only given for the resources of a classification project (the table lists the **final classifications** of the
  project), and the resources API, which is where a caller starts, does not have it;
- it is the resource's `token`, the same one in every table and valid until someone regenerates it with a web action
  *(from the source)*: a link that is leaked keeps working, and the API has no way to revoke or expire it.

**Proposal.** `GET storage/api/resources/<pk>/file` (and `/preview`, `/thumbnail`), with token authentication, `401`,
`403` and `404` told apart, and the file in the body whatever serves it, for any resource and not only those of a
classification project. Or, at least, give the download URL of a resource in the resources API.

**Workaround in the SDK.** For the resources of a classification project,
`classification_media.download_project_media_files()` uses those URLs: only a token, in parallel, with a ZIP if wanted.
For any other, `resources.download()` logs in with a web session (`user_name`/`user_password`), streams the file to disk
and retries network failures with tenacity.

## 37. Do not answer `deployment__isnull` with a `500`

**Labels:** bug, api

**Problem.** `ResourceFilter` declares `deployment__isnull = django_filters.BooleanFilter()` and
`GET storage/api/resources?deployment__isnull=true` (or `false`) answers `500` with an **HTML** page, on v1 and v2
(an empty value is fine). The resources without a deployment cannot be listed.

**Proposal.** Fix the filter (it is probably missing its `field_name` and `lookup_expr`, *not checked*), so that it
lists the resources with no deployment, and answer a server error with JSON.

**Workaround in the SDK.** `UnknownFilterWarning` names it, and the guide no longer lists it.

## 38. Read every list filter of a resource the same way

**Labels:** bug, api

**Problem.** The list filters take their lists in two ways and fail quietly with the other one (checked on v1 and
v2): `deployments` and `collections` read repeated parameters, `pk` and `locations_map` one string with commas.
`?deployments=1,2` is **ignored** and returns every resource (29 of 29), `?collections=2,3` is a `400`, `?pk=1&pk=2`
keeps one pk, and `?locations_map=1&locations_map=2` finds nothing. `locations_map` is ignored on v2 (it has no
maps).

**Proposal.** One convention (repeated parameters or commas) for all of them, and a `400` for a value that cannot
be read instead of ignoring it.

**Workaround in the SDK.** The list filters accept a list or a comma-separated string and are sent the way Trapper
reads each one; the SDK warns about `locations_map` on v2.

## 39. Do not turn every model field of a resource into a filter

**Labels:** enhancement, api

**Problem.** `ResourceFilter` excludes some fields and exposes the rest as filters, so the list accepts
`token`, `file_checksum_hash`, `file_size`, `mime_type` and `deployment` (checked: each one is applied on v1 and
v2). `token` is the secret that gives access to a resource with `?rt=`, and the list filters on it. Meanwhile
the useful ones are not documented.

**Proposal.** List the filters that are meant to exist, drop `token` and `file_checksum_hash`, and answer `400` to
the rest of the parameters (see entry 26).

**Workaround in the SDK.** The guide lists the filters each version applies.

## 40. Add an export endpoint for resources

**Labels:** enhancement, api

**Problem.** Locations and deployments have `.../export/` (a CSV), and resources do not:
`storage/api/resources/export` and `.../export/` answer `404` on v1 and v2.

**Proposal.** `GET storage/api/resources/export/`, with the same filters as the list and the same columns as the
list, plus the ones entry 35 asks for.

**Workaround in the SDK.** `resources.export()` builds the CSV from the JSON list, so it reads every page.

## 41. Download a set of resources through the API, asynchronously and by filters

**Labels:** enhancement, api

**Problem.** The files of several resources, those of a deployment, of a collection or of a filtered search, cannot be
asked for together. Two ways exist and neither is an API for resources:

- **The media table of a classification project** (`media_classification/api/media/<project_pk>/`, with the filters of
  the classifications list: deployment, collection, dates, species, ...) gives a URL with the resource's token for each
  file, which can be downloaded with no session (see entry 36). It works for **the resources of a classification
  project only**, and a caller must fetch the table and then make one request per file.
- **Trapper v1's web page** has *Generate data package* for the resources marked in the list
  (`POST storage/resource/data-package/`, with `resources_pks`, `package_name` and `metadata`). Checked on v1 with two
  resources: it answers `{"success": true, "msg": "...your data package is being generated now."}`, a celery task builds a
  ZIP, and the ZIP is served at `/accounts/data-package/<pk>/` with a web session (its files are `<pk>_<name>.<ext>`,
  plus a `00_METADATA.csv` with `metadata`, *from the source*). But it takes a **list of primary keys**, not filters; it
  refuses the whole package above `DATA_PACKAGE_MAX_SIZE`, 10 MB by default (*from the source*: about two hundred
  camera-trap photos); the answer **does not say which package it is** (no id, no task id) and the packages of an
  account are listed only on its profile page *(from the source)*; it takes no token; and **on v2 it does not exist**
  (`404`).

So for a resource that is in no classification project, or for a plain selection, the only way is one request per file
with a web session.

**Proposal.** An API endpoint, in v1 and v2, that takes the filters of the resource list (`deployments`, `collections`,
`rdate_from`, `tags`, ... or a list of pks), starts the packaging as a background task and answers with a task id;
`GET .../tasks/<id>/` with its state (see #9), and a download link that takes the token once it is ready. No fixed small
cap (or one the answer states), and a `404` that tells a missing file from a permission (entry 36).

**Workaround in the SDK.** For the resources of a classification project,
`classification_media.download_project_media_files()` and `download_collection_media_files()`: only a token, in parallel
(`parallel=True`), with a ZIP (`compress=True`), choosing with the filters of the media table. For any deployment or
collection, `deployments.download_resources()` and `collections.download_resources()` (and `resources.download_many()`):
one file at a time with a web session, choosing with the filters of the resource list or a `filter_fn`, skipping what
is already on disk, and reporting what failed; sequential, so slow for thousands of files.

## 42. Create, update and delete collections, and add or remove their resources, through the API

**Labels:** enhancement, api

**Problem.** `CollectionViewSet` is read-only: `OPTIONS storage/api/collections` answers `Allow: GET, HEAD, OPTIONS`
on v1 and v2. Creating an empty collection, editing it, deleting it, and adding or removing resources are web views:
`collection/create/`, `collection/update/<pk>/`, `collection/delete/<pk>`, `collection/append/` and
`collection/resource-delete/<pk>/` *(from the source, not tried on a server)*. The delete is a `BaseDeleteView`, which
deletes on a `GET` (see #13). The only way to create a collection **with** data is a package (entry 46).

**Proposal.** `POST storage/api/collections`, `PATCH`/`PUT`/`DELETE storage/api/collections/<pk>`, and
`POST`/`DELETE storage/api/collections/<pk>/resources`, with token authentication and the permissions the web views
check. Fields: `name`, `description`, `status`, `managers`.

**Workaround in the SDK.** None for these. A collection with resources can be created from a package
(`get_uploader()` and `collections.trigger_collection()`, see entry 46).

## 43. Return every field of a collection, and how many resources it has

**Labels:** enhancement, api

**Problem.** `GET storage/api/collections` gives nine keys (checked on v1 and v2): `pk`, `name`, `owner`,
`owner_profile`, `status`, `description`, `update_data`, `detail_data` and `delete_data`. The model has more, and the list
filters on some of them (`period_begin`, `period_end`, `cs_deployment`, `is_complete_cs_collection`, `managers`,
`members`, all applied on v1 and v2), but none is returned: not `date_created`, `period_begin`, `period_end`, `bbox`,
`managers`, `members` or the **number of resources**, which takes a request to
`storage/api/resources/collection/<pk>` to know. The last four keys are for the web page: URLs on v1 and `null` on v2,
and on v1 `delete_data` has no trailing slash (`/storage/collection/delete/2`) unlike the others.

**Proposal.** Return the fields of the model, the related objects as primary keys, and a `resources_count`, and leave
the web-page fields out.

**Workaround in the SDK.** The number of resources is `resources.get_by_collection(pk, page_size=1).pagination.count`;
the other fields cannot be read.

## 44. Give the collection endpoints one shape

**Labels:** enhancement, api

**Problem.** Three endpoints list collections and answer in three forms (checked on v1 and v2).
`storage/api/collections` and `collections_ondemand` are paginated with the nine fields; `collections_map` has the
same fields but is **one plain list** and ignores `page_size`; `collections_append` is a plain list of only `pk` and
`name`. `collections_ondemand` answers `404` on v2. `collections_map/<pk>` answers the detail too, and `collections/<pk>/` with a trailing slash is a `404` (see #21).

**Proposal.** One shape (the paginated one) for all, `fields` to choose what a caller needs, and the same endpoints in
v1 and v2.

**Workaround in the SDK.** `where_map()`, `get_append()` and the others wrap the plain list as one page, and
`where_ondemand()` raises `UnsupportedVersionError` on v2.

## 45. Reject a collection `status` that does not exist

**Labels:** bug, api

**Problem.** `status` is a plain `django_filters.Filter()` on the collection list: it compares the text as it is, in
upper and lower case, and a value that does not exist is an **empty result with a `200`**, not an error (checked on v1
and v2: `?status=private` and `?status=Bogus` give 0 collections, `?status=Private` gives them). The valid values
(`Private`, `OnDemand`, `Public`, `Archived`) are listed nowhere in the API. And `pk` reads a list as one string with
commas (`?pk=2,1`) and keeps one pk when it is repeated (`?pk=2&pk=1`), unlike `owners` and `research_projects`; see #38.

**Proposal.** A `ChoiceFilter` for `status` (a `400` with the valid ones), and one convention for the lists.

**Workaround in the SDK.** `CollectionStatus` resolves `status` in any case and raises `ValueError` listing the valid
values; `pk`, `owners`, `research_projects` and `locations_map` accept a list or a comma-separated string and are sent
the way Trapper reads each one; `UnknownFilterWarning` names what the list ignores (`locations_map` is ignored on v2).

## 46. Create a collection from a package through the API, and follow the task

**Labels:** enhancement, api

**Problem.** A collection with its resources is created from a package: a YAML and a ZIP uploaded to the account's
`collections/` folder, and `POST storage/api/collection/process/` to process them (checked on v1 and v2). The answer is
`200` with a `task_id` and the collection appears seconds later, but:

- **Nothing says when the task ends or how**: no endpoint for its state (#9). A file that is skipped (an identical one,
  or an extension Trapper does not accept) goes only to a `.log` next to the ZIP *(from the source)*.
- On v2 the **first call can answer `404`** ("The requested files were not found in your upload directory") because
  the uploaded files are moved into place a moment after the upload ends (seen once in a handful of runs). v1 answers the same
  with another message.
- The request names the files by their names in a folder of the account: no way to say which upload they are. The YAML
  needs a **classification** project (`project_id`) and deployments that exist, with the same timezone; a problem is a
  `400` with the details in `data.errors`, but the format itself is in `collection_schema.yaml`, not in the API.

**Proposal.** `GET .../tasks/<id>/` with the state and the per-file errors, an upload that is complete (and visible)
when its last request answers, and the schema of the YAML served by the API.

**Workaround in the SDK.** The guide describes the YAML and the requirements; `get_uploader()` and
`collections.trigger_collection()` do the two steps, and an e2e test tries again for a few seconds on v2. The task cannot
be followed: the SDK waits until the collection is listed.

## 47. Read the boolean parameters of the media table as booleans

**Labels:** bug, api

**Problem.** `GET media_classification/api/media/<project_pk>/` reads `trapper_url`, `trapper_url_token`,
`private_human` and `private_vehicle` with `query_params.get(name, "True") == "True"`: only the exact text `True`
is true, and `true`, `1` or any other text is **false, with no error** (checked on v1 and v2, project 2, which has two
images of humans: by default 26 files are public and 2 private, with `private_human=True` the same, and with
`private_human=true` or `False` all 28 are public; `trapper_url_token=false` takes the token out of every URL). Every
other boolean filter of the API accepts `true`/`false`, and a client that sends a boolean the usual way (Python's
`True` is sent as `true`) gets the **opposite** of what it asked: `private_human=True` shows the files of the humans.
Also `trapper_url` is read and does nothing: `trapper_url=False` still gives absolute URLs (v2; in the source it is
parsed and never passed on).

**Proposal.** Read them like the filters of the same endpoint (`true`/`false`, any case), answer `400` for a value that
is neither, and drop `trapper_url` or make it work.

**Workaround in the SDK.** `private_human`, `private_vehicle`, `trapper_url` and `trapper_url_token` are sent as the text
`True`/`False` whatever boolean (or `true`/`false` text) the caller gives, and anything else is a `ValueError`.

## 48. Answer an empty media or results table with an empty list, not a `400`

**Labels:** bug, api, cross-cutting

**Problem.** `media_classification/api/media/<project_pk>/` and `media_classification/api/classifications/results/<project_pk>/`
answer `400 ["Empty queryset or you have no permission to access the requested objects."]` when the filters leave no
row (checked on v1 and v2: `?rdate_from=2030-01-01`), while the list of classifications with the same filter answers
`200` with `count: 0`. It is the same problem as #31, in two more endpoints: a filter that matches nothing and a
missing permission look alike.

**Proposal.** As in #31: `200` with the header row only, and `403` for a missing permission.

**Workaround in the SDK.** The results and media components read this `400` as an empty result (`get_*`, `where_*`,
`export_*` and the downloads), which hides a missing permission too: the two cannot be told apart.

## 49. Let the media table be read in pages

**Labels:** enhancement, api

**Problem.** The media table is built in memory and sent as **one gzip CSV with every row**: `page` and `page_size` are
ignored, and `page=2` answers the same rows as `page=1` (checked on v2, project 2: 28 rows with `page_size=5`, and
`pages=1`). **The results table does the same** (`classifications/results/<project_pk>/`, checked on v2: 28 rows with or
without `page_size=5`; see #55). The request for a project with many resources takes as long as the whole table, with no way to ask for a
part of it, and the client cannot tell how big the answer will be beforehand. The list of classifications, which has
the same filters, is paginated. `wildintel-zooniverse` says in its code that for a very large collection (R0038, about
876,000 images) one request takes longer than the client's timeout, so it asks one deployment at a time *(its own
comment, not checked here)*.

**Proposal.** Paginate it like the other lists (with `count`), or document a limit and give a `Link`/`next` header.

**Workaround in the SDK.** Filtering by `deployment` and by `collection` makes the answer smaller, one deployment at a
time. The guide says that paging is ignored. *(Not checked: how long a table of tens of thousands of rows takes.)*

## 50. Say in the media table what each image shows, and fill `exifData`

**Labels:** enhancement, api

**Problem.** A row of the media table has eleven columns (`mediaID`, `deploymentID`, `captureMethod`, `timestamp`,
`filePath`, `filePublic`, `fileName`, `fileMediatype`, `exifData`, `favorite`, `mediaComments`; the same on v1 and v2)
and nothing about what is in the file: not the observation type, the species, the count or a bounding box. Yet the
table is filtered by them (`species`, `observation_type`, `sex`, `age`) and `private_human` uses the observation type
to hide a file. To know what an image shows, a client asks the results table (`classifications/results/<pk>/`) and joins
the two by `mediaID`. And `exifData` is always empty: in the source the column is created with `None` for every row.

**Proposal.** An option to add `observationType` and `scientificName` to the media rows, or one table with the media
and its observations, and either fill `exifData` or drop the column.

**Workaround in the SDK.** The guide has the join by `mediaID` (the media table with `where_project_media()`, and the
results with `where_project_results()`).

## 51. Filter by the collection's own pk, not by its link to the classification project

**Labels:** bug, api

**Problem.** The `collection` filter of the classification endpoints (the list, the results table and the media table)
takes the pk of the **link between the project and the collection** (`ClassificationProjectCollection`), not the pk of
the storage collection that a user knows, and no endpoint says so. Checked on v1: a project with links 3 and 4, to the
collections 2 and 3: `?collection=2` is a `400` ("Select a valid choice. 2 is not one of the available choices"), and
`?collection=3`, which a user takes for collection 3, answers the files of **link 3, that is of collection 2** (20 rows
instead of 8), with no error. On the v2 test data both pks are equal, so the mistake does not show there. Without `project` in the query,
the list answers the same `400` for `deployment` and `collection` (the choices are those of the project), which reads as
if the pk did not exist.

**Proposal.** Accept the collection's pk, which is what the rest of the API calls `collection`, and put the project in
the message of the `400`.

**Workaround in the SDK.** `where_collection_media()` and `get_collection_media()` translate the collection's pk into
its link; `where_project_media(collection=...)` and `where_project_results(collection=...)` take the link's pk as they
are given.

## 52. Make `private_species` of the media table work

**Labels:** bug, api

**Problem.** `private_species` is meant to hide the files of some species, like `private_human` and `private_vehicle`,
and the view reads it with `query_params.getlist("private_species", [])`. But `GET media_classification/api/media/<project_pk>/`
answers **`500`** for any value (checked on v1 and v2, project 2: `?private_species=1`, `=1&private_species=2`, `=999999`
and an empty `?private_species=`), while the same request without it answers the table. The cause was not found: the
values arrive as text and are compared with the `speciesID` column of the table (`is_in(private_species)`), which could
be the mismatch *(a guess, not checked)*. A caller has no way to hide a species.

**Proposal.** Convert the values to the type of the column, reject a value that is not a species pk with a `400`, and
answer the table.

**Workaround in the SDK.** The guide says not to use it. To hide a species, filter the rows on the client with the
results table (the observation type and the species of each `mediaID`) and leave those files out of the download.

## 53. Create, update and approve classifications through the API

**Labels:** enhancement, api

**Problem.** The classification list and the user classification list answer `Allow: GET, HEAD, OPTIONS` on v1 and v2,
and the only write in all of `media_classification/api` is `POST classifications/import/`. To classify a resource, correct a
species or approve a result there are the web views (`classify/<pk>/`) and nothing else. The one script-friendly way
to change what exists is the import: export the results table with `camtrapdp=False`, edit it and import it with its
`_id` column. That has limits: it only **updates** classifications that already exist (an `_id` that is not one of the
project's is rejected), it runs in the background with no way to follow it (#9), and an invalid table is a bare `500`
(#10). A script that classifies, for example a model that proposes a species, has to build a CSV for it.

**Proposal.** `POST`/`PATCH` on a classification (its observations and its approval), with the permissions of the web
view, and a `400` with the errors in JSON.

**Workaround in the SDK.** `classification_results.import_classifications()`: the guide describes the export, edit and
import cycle. It cannot create a classification for a resource that has none.

## 54. Return in the classification list the fields the results table has

**Labels:** enhancement, api

**Problem.** A row of the list has `dynamic_attrs` with only `observation_type`, `species` and `count` (plus
`confidence`) (checked on v1 and v2), and the species is a text (`"European Rabbit (Oryctolagus cuniculus)"`), not a
primary key. `sex`, `lifeStage`, `behavior`, `individualID` and the bounding boxes, which the results table carries, are
missing, although the list filters by `sex` and `age`. The row has no primary key of the project either, only its name in
`classification_project`, and its `collection` is the pk of the link with the project (#51). A client that wants to show
or edit a classification has to ask the results table and join it with the list by `_id` (which is the `pk` of the list
row, checked) or by `mediaID`.

**Proposal.** The same attributes in both, the species with its pk, and the pk of the project.

**Workaround in the SDK.** The guide says which one to use for what: the results table to know what an image shows.

## 55. Document the format of the results table that can be imported, and what `observationID` is

**Labels:** bug, api

**Problem.** `GET classifications/results/<project_pk>/` answers two formats (checked on v1 and v2: the same columns on
both). With `camtrapdp=True`, **the default**, there are 28 columns and no `_id`; with `camtrapdp=False` there are 32:
`_id`, `countNew`, `englishName` and `bboxes` are added. The import requires `_id`, so the table you get by default cannot
be imported again, and nothing in the API says that the other format is the one for that. The table has two
identifiers and they are not explained: `_id` is the pk of the final classification (it equals the `pk` of the list row,
checked: 5 and 5 on v1, 6 and 6 on v2), and `observationID` is **only the position of the row in the table that was
asked** (in the source it is a counter from 1 that is reset after the rows are sorted; checked on v2: the same
observation is 4 in the whole table and 1 with `sex=male`, while its `_id` stays 6; on v1 it is also 4 with `camtrapdp=False`
and 28 with `camtrapdp=True`). It is not a key, it changes with every filter and format, and the list does not have it.
`_id` is the classification's, not the observation's: **two observations of one image share it** (checked on v1 and v2: a
rabbit and a lynx in one image are two rows with `_id` 6), so an observation has no identifier at all. The table also ignores `page` and `page_size`, like the media table (#49):
`page_size=5` and `page=2` return the same 28 rows.

**Proposal.** Say which format is the one to import (or give a single format that serves to read and to import), explain
the two identifiers (or do not put a row counter in a column called `observationID`), and paginate it.

**Workaround in the SDK.** `ClassificationResultRecordCamtrapDP` and `ClassificationResultRecordTrapper` are the two
formats, and the guide says to use `camtrapdp=False` for the cycle of exporting, editing and importing.

## 56. Use one shape for `bboxes` in both versions, and do not fail the whole results table for one row

**Labels:** bug, api

**Problem.** The boxes of an observation are stored differently: Trapper v1 keeps a **list of boxes**
(`[[x, y, w, h], [x, y, w, h]]`), v2 **one box**, `[x, y, w, h]`, "for the first occurrence of given object" (the
comment of its model). `GET classifications/results/<project_pk>/` reads each its own way, and a row with the other
shape makes the default format (`camtrapdp=True`) answer **`500` for the whole project**: v2 with `[[x, y, w, h]]` (a
polars `ComputeError: error deserializing JSON ... as numeric` in `_process_bboxes`) and v1 with `[x, y, w, h]`
(checked on both, writing rows from a shell, which skips the forms; whether the web form, the import or the AI worker
check the shape was not checked). The `camtrapdp=False` format passes the text as it is stored and keeps working.
In the default format v1 gives **one row per box, each with `count` 1** (an observation of `count` 2 with two boxes is
two rows), and v2 one row per observation: the same data, a different table.

**Proposal.** One shape, documented, in both versions; reject a wrong one when it is saved; and give the row with a
bad value as an error of its own instead of a `500` for every other row of the project.

**Workaround in the SDK.** The guide has the table of boxes per version. `ClassificationResultRecordTrapper` reads both
shapes (the v1 list and the v2 box) as a list of `BBox`, and the row class is picked by the `_id` column, so a row it cannot
read is an error and not a row of the wrong class.

## 57. Do not fetch the Camtrap DP schema from the internet in every classification import

**Labels:** bug, api

**Problem.** `POST classifications/import/` answers `200` ("You have successfully run a celery task. Classifications
are being imported now.") and the task then downloads
`https://raw.githubusercontent.com/tdwg/camtrap-dp/1.0.2/observations-table-schema.json` to validate the table. On a
server that cannot reach GitHub the task ends in `FAILURE` (`ConnectionError ... Temporary failure in name resolution`,
seen in the task result on v2) and nothing changed, and the API gave no sign of it (#9). Checked once, on v2; v1 was
not checked.

**Proposal.** Ship the schema with Trapper (or cache it), and answer the failure through the task state (#9).

**Workaround in the SDK.** None: the import returns the message and the `task_id`, and the failure can only be seen in
the task result, or because the classifications did not change.

## 58. Answer `classified` and `classified_ai` in the results and media tables

**Labels:** bug, api

**Problem.** `ClassificationFilter` has `classified` and `classified_ai`, which filter on `classified_user` and
`classified_ai`, two annotations that only the list view (`ClassificationViewSet.get_queryset`) adds to the queryset. The
results table (`classifications/results/<project_pk>/`) and the media table (`media/<project_pk>/`) use the same
filter without them, and on **v2 answer `500`** to `?classified=true`, `?classified=false` and `?classified_ai=true`
(checked; the list answers, `27` and `1` of the `28`). v1 answers them in the three. The trap-rate table (`classifications/results/agg/<project_pk>/`)
does the same on v2 (checked).

**Proposal.** Add the annotations to the two views, or take the filters out of those endpoints.

**Workaround in the SDK.** The guides say it. *(No workaround: filter on the client with the list, which has them.)*

## 59. Call the filter for an approved classification the same in v1 and v2

**Labels:** bug, api, cross-cutting

**Problem.** The filter for "approved" is `approved` on v2 and `status` on v1, in the list, the results table and the media
table (checked in the three, on both versions: `approved=true` gives 24 of 28 on v2 and the 28 on v1, `status=true` the
reverse). The version that does not know a name ignores it **without an error** and returns everything (#38), and the
field of the row is `approved` in v2 and `status` in v1 too. A script written for one version silently stops filtering on the
other.

**Proposal.** The same name in both, and the old one kept as an alias for a while.

**Workaround in the SDK.** `approved=True` is sent as `status` on v1, so the one name works on both; `status` on v2 and any
other name the server version ignores are warned about (`UnknownFilterWarning`).

## 60. Make `approved` work in the AI results table of v2

**Labels:** bug, api

**Problem.** `AIClassificationFilter` (v2) filters `approved` on the field `approved`, an annotation that only the list view
(`AIClassificationViewSet.get_queryset`) adds. The AI results table (`ai-classifications/results/<project_pk>/`) uses the
same filter without it and answers **`500`** (`FieldError: Cannot resolve keyword 'approved'`) to `?approved=true` (checked).
v1 answers.

**Proposal.** Add the annotation to `AIClassificationResultsView`, or filter on `is_approved` of the derived final one.

**Workaround in the SDK.** `export(approved=...)` on v2 emits an `UnknownFilterWarning` before the request. *(No
workaround for the filter itself: filter the list.)*

## 61. Return the same fields in the AI classification list of v1 and v2

**Labels:** api, consistency

**Problem.** The v2 AI list (`ai-classifications`) has no `owner`, `owner_profile`, `classification` or `created_at`, and
sends `updated_at: null`; v1 sends them all. The user list of v2 keeps `owner`. Who ran the model, and when, is lost, and
a client written for v1 breaks on v2 (the SDK raised `ValidationError`).

**Proposal.** Return the same fields in both (`owner` = who requested the run, `created_at`).

**Workaround in the SDK.** Those fields are optional (`None` on v2).

## 62. Use one scale for the confidence of an AI classification

**Labels:** api, consistency

**Problem.** The `confidence` filter reads a fraction (`confidence=0.9`, both versions; `90` gives nothing). The list gives
it as a fraction in v1 (`"classification_confidence": "0.93"`, a string) and as a percentage in v2, inside each attribute
(`"species": {"value": "...", "confidence": 93.0}`), with no `classification_confidence`.

**Proposal.** One scale (a fraction, as the filter and the Camtrap DP `classificationProbability`) and a number, not a
string.

**Workaround in the SDK.** `classification_confidence` is the fraction as text (`"0.93"`) on both versions.

## 63. Filter the user and AI lists by deployment or collection without the project

**Labels:** api, usability

**Problem.** `deployment` and `collection` of the user and AI lists are checked against the deployments and collections of
`project`. Without `project`, v1 answers `404 No ClassificationProject matches the given query` and v2 `400 Select a
valid choice. 3 is not one of the available choices` — both read as if the deployment did not exist. The final
classification list (`classifications`) does the same.

**Proposal.** Check them against what the user can see when there is no `project`, or answer a `400` that names `project`.

**Workaround in the SDK.** A `ValueError` that asks for `project`, before the request.

## 64. Apply the same filters to the user and AI lists in v1 and v2

**Labels:** api, consistency

**Problem.** In v1 the AI list applies only `project`, `deployment`, `collection`, `ftype`, `species`, `observation_type`,
`bboxes`, `approved`, `confidence` and `ai_provider` (and custom attributes); `owner`, `user`, `feedback`, `locations_map`,
`rdate_*`, `rtime_*`, `sex` and `age` are ignored **without an error** (`rdate_from=2030-01-01` returns every row). The v1
user list has no `sex`, `age`, `classified` or `classified_ai`. v2 applies all of them.

**Proposal.** The same filters in both (v2's set), or a `400` for an unknown one.

**Workaround in the SDK.** `UnknownFilterWarning` for a filter the server's version does not apply.

## 65. Read `camtrapdp` (and every boolean) as a boolean, and say "no species" with `null`

**Labels:** api, cross-cutting

**Problem.** The results tables read `camtrapdp` with `== "True"`: `camtrapdp=true` (what most HTTP clients send for a
boolean, the SDK included) gives Trapper's format. The same as the media table (entry 47). And the user and AI lists write
a missing species as the text `"None"` (`str(None)`), in v1 and v2.

**Proposal.** Read booleans with the same parser as the filters (`true`/`false`/`1`/`0`), and send `null` for no species.

**Workaround in the SDK.** `camtrapdp` is sent as `True`/`False`; `"None"` is read as `None`.

## 66. Read the list parameters of the data package (`keywords`, `licenses`, `private_species`)

**Labels:** bug, api

**Problem.** `ResultsDataPackageGeneratorParams` types `keywords`, `licenses` and `private_species` as `List`, but
`AbstractParams.from_query_params` reads one text per parameter (`query_params.get`) and `List("a")` fails, so the text is
kept. Every request with them fails (checked, v1 and v2): `keywords=a` → `400 'a' is not of type 'array'`, `licenses=x` →
`400 'str' object has no attribute 'name'`, `private_species=3` → `400 'is_in' cannot check for List(String) values`.
The package can only have the research project's keywords and `private` licenses.

**Proposal.** Read them with `query_params.getlist` (repeated parameters, or comma-separated), and `licenses` as names
of licenses.

**Workaround in the SDK.** A `ValueError` that says so, before the request.

## 67. Make `release` and `get_released` of the data package work, and never cache two packages for one key

**Labels:** bug, api

**Problem.** The API saves every package as `CLASSIFICATION_RESULTS_CACHE` (with `released` from `release`), and
`get_released` looks for `CLASSIFICATION_RESULTS` packages: a release made through the API is never found. When there is
none, `get_released=True` builds a new package with the same `cache_key` (the flags are left out of the key) **without
deleting the cached one**. From then on `_check_cache` does `UserDataPackage.objects.get(...)` on two rows and every request
with those parameters, `clear_cache=true` included, answers `400 get() returned more than one UserDataPackage` (checked
on v2; it needed deleting one in the database).

**Proposal.** `get_released` with no release: say so (`404`) instead of building one; use `filter(...).first()` (or a
unique constraint) for the cache; let the API release a package as `CLASSIFICATION_RESULTS`.

**Workaround in the SDK.** The error says what happened and that an admin has to delete one; the docs warn.

## 68. Do not fail the data package of a project with no admin

**Labels:** bug, api

**Problem.** On v1 the package's `contributors` are the admins of the classification project
(`classification_project_roles` with role admin). A project with none answers `400 [package-error] ... [] should be
non-empty at property 'contributors'`, which does not say what to do. Also, the download URL answers `200` with an empty
body and `X-Accel-Redirect` when Trapper is not behind its nginx.

**Proposal.** Fall back to the project's owner (or the research project's), or answer a `400` that names the cause.

**Workaround in the SDK.** The error adds "give the project an admin role"; the download says when there is no proxy.

## 69. Limit the sequences to what the user can see, and fix their `search`

**Labels:** bug, security, api

**Problem.** `SequenceViewSet.get_queryset` returns `Sequence.objects.all()`: any user with a token sees every sequence
of the server and the PKs of their resources (checked, v1 and v2, with a user with no role: 14 and 23 sequences). Its
`search_fields` has `name`, which a sequence does not have: `?search=` answers `500`. `deployment` reads only
comma-separated PKs (a repeated parameter keeps one), unlike the other list filters. On v2 `resources` repeats a resource
once per classification of it.

**Proposal.** Filter by the classification projects the user can see; drop `name` from `search_fields`; accept repeated
`deployment`; `distinct()` the resources.

**Workaround in the SDK.** `search` is warned about; `deployment` is sent comma-separated; `resources` without repeats.

## 70. Do not show every account and its email to every user, and let the user list be filtered

**Labels:** security, privacy, api

**Problem.** `UserViewSet` returns `User.objects.all()` with `email` to any authenticated user (checked, v1 and v2, with
a user with no role: the 5 accounts and their emails). It has no filter and no `search`: every parameter is ignored
without an error, so finding one user means reading them all.

**Proposal.** Show the email only to the user itself and to admins (or the members of shared projects); add
`username` and `search` filters.

**Workaround in the SDK.** `UnknownFilterWarning` for any filter; the docs show a client-side lookup.

---

## Done

*(nothing yet)*
