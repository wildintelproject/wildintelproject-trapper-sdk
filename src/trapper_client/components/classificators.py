"""
Component for Classificators data endpoint.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificatorCreate, Classificator


class ClassificatorsComponent(TrapperComponent[Classificator]):
    """
    Component for ``/media_classification/api/classificators/``.

    Retrieve and filter classificators (AI/human classifier configurations) from Trapper.

    Main endpoints:
    - ``GET /media_classification/api/classificators``: List of classificators (paginated)
    - ``GET /media_classification/api/classificators/{pk}``: Single classificator detail

    **Available filter fields:**

    | Parameter  | Type    | Description                               |
    |------------|---------|-------------------------------------------|
    | owner      | boolean | true = classificators owned by the user   |
    | search     | string  | Search by name or description             |

    Returns a paginated list of classificators with support for filtering
    through query parameters.
    """

    endpoint = "/media_classification/api/classificators"
    schema = Classificator
    create_endpoint = "media_classification/classificator/create/"
    _CREATED_RE = re.compile(r"/classificator/update/(\d+)/")

    def create(
        self,
        classificator: ClassificatorCreate,
        *,
        raise_on_error: bool = True,
    ) -> Classificator | None:
        """Create a classificator (**Trapper v1 only**).

        The REST API is read-only for classificators, so this simulates the classic web form
        ``media_classification/classificator/create/`` with cookie/session authentication, as
        :meth:`~trapper_client.components.research_projects.ResearchProjectsComponent.create` does.
        The account that logs in becomes the owner.

        Trapper silently drops a species primary key that does not exist: a classificator whose
        ``species`` are all unknown ends up accepting every species. Check the keys against
        ``client.species`` first when it matters.

        Only the standard attributes are covered: species, tracked species, the optional
        attributes (sex, age, ...) and the layout. Custom and predefined attributes are not.

        Warning:
            It depends on an unversioned HTML form, and needs ``user_name``/``user_password`` (the
            *email* on servers that log in by email): a token alone cannot authenticate it.

        Args:
            classificator: A :class:`~trapper_client.schemas.classificators.ClassificatorCreate`,
                which validates it before anything is sent.
            raise_on_error: Raise ``APIError`` when the server rejects the form (the default);
                with ``False`` return ``None`` instead.

        Returns:
            The created classificator, or ``None`` when the server rejected the form and
            ``raise_on_error=False``.

        Raises:
            TypeError: ``classificator`` is not a ``ClassificatorCreate``.
            err.UnsupportedVersionError: On Trapper v2.
            err.APIError: The server rejected the form (a name already in use, unknown species,
                ...) or redirected to its login page.

        Example::

            clf = client.classificators.create(
                ClassificatorCreate(
                    name="Iberian mammals",
                    species=[12, 15, 40],
                    tracked_species=[40],
                    sex=True,
                    age=True,
                )
            )
        """
        self._require_version("v1", feature="classificators.create()")
        if not isinstance(classificator, ClassificatorCreate):
            raise TypeError(
                f"create() takes a ClassificatorCreate, not {type(classificator).__name__}; "
                "build one with ClassificatorCreate(...) or ClassificatorCreate.model_validate(data)"
            )

        response = self._submit_create_form(
            self.create_endpoint, classificator.to_form(), "Classificator", raise_on_error,
            field_prefix="classificator-",
        )
        if response is None:
            return None
        # Trapper redirects to the update page of the classificator it has just saved
        created = self._CREATED_RE.search(response.headers.get("location") or "")
        return self.find(int(created.group(1))) if created else None
