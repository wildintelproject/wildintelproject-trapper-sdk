"""The filters of the classification list, the results table and the media table (``ClassificationFilter``)."""
from __future__ import annotations

from typing import Any, Dict

from trapper_client import err

#: Filters that both Trapper versions apply (checked on v1 and v2, and on the three endpoints).
_COMMON = frozenset({
    "project", "owner", "deployment", "collection", "locations_map",
    "rdate_from", "rdate_to", "rtime_from", "rtime_to", "ftype",
    "classified", "classified_ai", "bboxes", "species", "observation_type", "sex", "age",
    # fields of the model: Trapper makes a filter of each
    "pk", "resource", "sequence", "date_recorded", "is_setup", "has_bboxes",
})

CLASSIFICATION_FILTERS = {
    # v1 calls "approved" ``status``, and ignores ``approved`` and ``is_approved``
    "v1": _COMMON | {"status", "status_ai", "has_initial_data"},
    # v2 calls it ``approved`` (and ``is_approved``), and ignores ``status``
    "v2": _COMMON | {
        "approved", "is_approved", "is_blank", "is_gold_standard", "has_animals", "has_humans",
        "has_vehicles", "has_unknown", "classification_type", "model", "final_classification",
    },
}


def true_false(name: str, value: Any) -> str:
    """A boolean parameter as Trapper reads it: it compares it with the text ``"True"``.

    A Python ``True`` goes over HTTP as ``true``, which Trapper took as false. A boolean, or the text
    ``true``/``false`` in any case, is accepted; anything else is a ``ValueError`` before the request.
    """
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return "True" if value.strip().lower() == "true" else "False"
    raise ValueError(f"{name} must be True or False, not {value!r}")


def camtrapdp_param(query: Dict[str, Any]) -> Dict[str, Any]:
    """``camtrapdp`` of the results tables as Trapper reads it (``camtrapdp=True`` used to give Trapper's format)."""
    if "camtrapdp" in query:
        query = dict(query)
        query["camtrapdp"] = true_false("camtrapdp", query["camtrapdp"])
    return query


class ClassificationFiltersMixin:
    """``known_filters`` and a portable ``approved`` for the components that use ``ClassificationFilter``.

    ``extra`` parameters of an endpoint (``camtrapdp``, ``private_human``, ...) are added by each component.
    """

    #: Parameters of the endpoint that are not filters.
    extra_params: frozenset = frozenset()

    #: The filters also depend on the project: Trapper adds one for each custom attribute of its classificator.
    unknown_filter_hint = "; or the name of an attribute of the project's classificator"

    @classmethod
    def _filters_for(cls, extra: frozenset) -> Dict[str, frozenset]:
        return {version: names | extra for version, names in CLASSIFICATION_FILTERS.items()}

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """``approved`` on Trapper v1, where the same filter is called ``status`` (v1 ignores ``approved``)."""
        query = camtrapdp_param(query)
        if "approved" in query and self.client.server_version == "v1":
            query = dict(query)
            query.setdefault("status", query.pop("approved"))
        return query

    def _is_empty_result(self, exc: Exception) -> bool:
        """The results table and the media table answer ``400 "Empty queryset ..."`` when no row matches.

        The same ``400`` is the answer to a missing permission, so the two cannot be told apart.
        """
        return isinstance(exc, err.BadRequestError) and "Empty queryset" in str(exc)


class RequireProjectMixin:
    """``deployment`` and ``collection`` of a classification list need ``project``.

    Trapper checks them against the project's own: without ``project`` it answers ``400 "Select a valid choice.
    19 is not one of the available choices"`` (v1 answers ``404 No ClassificationProject matches`` in the user and
    AI lists), which reads as if the deployment did not exist. The SDK raises a ``ValueError`` before the request.
    A project-scoped call (``overwrite_endpoint``, with the project in the URL) needs nothing.
    """

    #: A way out added to the message (``"or use where_project_results() ..."``).
    project_hint: str = ""

    def _require_project(self, query: Dict[str, Any] | None, kwargs: Dict[str, Any]) -> None:
        if kwargs.get("overwrite_endpoint") or getattr(self.client, "api_flavor", None) == "ninja":
            return  # the lists of the new API take them without project
        given = {**(query or {}), **kwargs}
        needing = [name for name in ("deployment", "collection") if name in given]
        if needing and "project" not in given:
            hint = f", {self.project_hint}" if self.project_hint else ""
            raise ValueError(
                f"{' and '.join(needing)} of {self.endpoint} need project=<pk>: Trapper checks them against the "
                f"project's own and otherwise answers an error that reads as if they did not exist. "
                f"Add project{hint}."
            )

    def get(self, query: Dict[str, Any] | None = None, *args: Any, **kwargs: Any):
        """One page of the list; see :meth:`TrapperComponent.get`. ``deployment`` and ``collection`` need ``project``."""
        self._require_project(query, kwargs)
        return super().get(query, *args, **kwargs)

    def where(self, query: Dict[str, Any] | None = None, *args: Any, **kwargs: Any):
        """Lazy iteration; see :meth:`TrapperComponent.where`. ``deployment`` and ``collection`` need ``project``."""
        self._require_project(query, kwargs)
        return super().where(query, *args, **kwargs)

    def get_all(self, query: Dict[str, Any] | None = None, *args: Any, **kwargs: Any):
        """Every page; see :meth:`TrapperComponent.get_all`. ``deployment`` and ``collection`` need ``project``."""
        self._require_project(query, kwargs)
        return super().get_all(query, *args, **kwargs)
