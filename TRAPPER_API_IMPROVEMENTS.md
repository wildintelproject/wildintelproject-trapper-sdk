# Trapper API: proposed issues

Draft issues for the Trapper project, found while building `wildintel-trapper-sdk`. Each one is
written to be copied to the tracker as it is: title, what happens today, what is proposed, and what
the SDK does in the meantime.

- **Checked against:** the Trapper v1 source (`development`, v1.7.3-63) and a live v1.7.4 server.
- **Trapper v2:** not checked unless an issue says so. Re-check each one before filing it.
- Add new issues at the end, keep the numbering, and move a closed one to the *Done* list.

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

---

## 1. Add an endpoint to create research projects

**Labels:** enhancement, api

**Problem.** `ResearchProjectViewSet` is a `PaginatedReadOnlyModelViewSet`. A research project can
only be created through the web form `research/project/create/`, so a script or integration cannot
create one.

**Proposal.** `POST research/api/projects/`, authenticated with a token, answering `201` with the
project as `GET research/api/projects/<pk>/` shows it. As in the form, the authenticated user
becomes the owner and a project administrator, and a non-staff user's project stays *not approved*
until an administrator approves it.

Fields: `name`, `acronym` (3 to 10 characters; both unique), `sampling_design`, `sensor_method`,
`animal_types`, `bait_use`, `event_interval`, `keywords`, `abstract`, `methods`, `description`.

**Workaround in the SDK.** `research_projects.create()` simulates the form with a cookie session and
a CSRF token. It needs `user_name`/`user_password` (the *email* on servers that log in by email), so
a token alone cannot create a project.

## 2. Add update and delete endpoints for research projects

**Labels:** enhancement, api

**Problem.** `research/project/update/<pk>/` and `research/project/delete/<pk>/` are web views only.
The serializer already tells the client whether the user may use them (`update_data`,
`delete_data`), but there is no API call to use them with.

**Proposal.** `PATCH`/`PUT`/`DELETE research/api/projects/<pk>/`, honouring the existing role
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
collection (`POST`/`DELETE research/api/project/<pk>/collections/`).

**Workaround in the SDK.** None.

## 7. Add create endpoints for classification projects and classificators

**Labels:** enhancement, api

**Problem.** `ClassificationProjectViewSet`, `ClassificationProjectCollectionViewSet` and
`ClassificatorViewSet` are all read-only. Creating a classification project (`project/create/`),
linking a collection to it (`project/collection/add/`) and creating a classificator
(`classificator/create/`) are web forms.

**Proposal.** `POST media_classification/api/projects/`, `POST .../project/<pk>/collections/` and
`POST media_classification/api/classificators/`, answering `201`. A classificator is a taxonomy and
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

---

## Done

*(nothing yet)*
