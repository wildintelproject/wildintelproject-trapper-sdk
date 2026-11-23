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

**Workaround in the SDK.** For locations, `UnknownFilterWarning` names the filters the server would ignore; the
filters each version applies are listed in the locations guide. Other endpoints are not checked yet.

---

## Done

*(nothing yet)*
