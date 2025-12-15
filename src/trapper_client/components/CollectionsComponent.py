from typing import Dict, Any, Callable, TypeVar

from trapper_client import Schemas
from trapper_client.TrapperAPIComponent import TrapperAPIComponent, T
import attr

#
# Collection
#

@attr.s
class CollectionsComponent(TrapperAPIComponent):
    """
    Component for interacting with Collections endpoint.

    Provides methods to retrieve and filter collections from the Trapper API.
    """

    explicit_fields = [
        "name",
        "status",
        "owner",  # OwnCollectionBooleanFilter
        "research_projects",
        "owners",
        "locations_map",
    ]

    def __attrs_post_init__(self):
        """
        Initialize the component with collections endpoint and schema.
        """
        self._endpoint = "/storage/api/collections"
        "/api/collections",  # ViewSet principal para collections
        #"/api/collections_ondemand",  # ViewSet para collections on-demand
        #"/api/collections_map",  # ViewSet para collections con mapas
        #"/api/collections_append",  # ViewSet para añadir recursos a collections

        self._schema = Schemas.TrapperCollectionList

    def __init_subclass__(cls, **kwargs):
        """
        Dynamically generates getter methods with docstrings
        for each explicit field when the subclass is created.
        """
        super().__init_subclass__(**kwargs)

        for field in cls.explicit_fields:

            def make_getter(f, all_results=False):
                prefix = "get_all_by_" if all_results else "get_by_"
                method_name = f"{prefix}{f}"

                doc = f"""
Auto-generated method for querying Collections by field '{f}'.

Parameters
----------
value : Any
    Value to filter by for field '{f}'. Can be a single value or a list
    (lists will be joined by commas).
query : dict, optional
    Additional query parameters to include.
filter_fn : callable, optional
    Optional function to filter results locally after fetching.
endpoint : str, optional
    Optional endpoint override.

Returns
-------
T
    A Pydantic model containing the filtered results.
"""

                def getter(self, value, query=None, filter_fn=None, endpoint=None):
                    query = query or {}
                    if isinstance(value, list):
                        value = ",".join(map(str, value))
                    query[f] = value
                    if all_results:
                        return self.get_all(query, filter_fn=filter_fn, endpoint=endpoint)
                    return self.get(query, filter_fn=filter_fn, endpoint=endpoint)

                getter.__name__ = method_name
                getter.__doc__ = doc
                return getter

            setattr(cls, f"get_by_{field}", make_getter(field, all_results=False))
            setattr(cls, f"get_all_by_{field}", make_getter(field, all_results=True))

    def get_by_id(self, pk: int, query: dict = None) -> T:
        """
        Retrieve collection by ID.

        Parameters
        ----------
        project_id : int
            The ID of the collection.

        Returns
        -------
        T
            The collection with the specified vaID.
        """
        return self.get_by_pk(pk, query)

    def get_by_research_project(self, project_id: int, query: dict = None) -> T:
        """
        Retrieve collections associated with a research project.

        Parameters
        ----------
        project_id : int
            The ID of the research project.

        Returns
        -------
        Schemas.TrapperCollectionList
            Collections associated with the specified research project.
        """
        endpoint = f"/research/api/project/{project_id}/collections"
        res = self._client.get_all_pages(endpoint, query)
        return self._schema(**res)


    def trigger_collection(
        self,
        collection_id: int,
        payload: Dict[str, Any],
        endpoint: str | None = None,
        raise_on_error: bool = True,
    ):
        """
        Trigger collection processing on the server.

        Parameters
        ----------
        collection_id : int
            Collection ID.
        payload : dict
            Payload sent to the server.

            Example
            -------
            payload = {
                "yaml_file": "package_123.yaml",
                "zip_file": "package_123.zip",
                "remove_zip": False
            }

        endpoint : str, optional
            Optional endpoint override.
        raise_on_error : bool, optional
            Whether to raise on API error.

        Returns
        -------
        requests.Response
        """

        actual_endpoint = (
            endpoint
            or f"{self._endpoint}/{collection_id}/trigger"
        )

        self._client.logger.info(
            "Triggering collection %s with payload %s",
            collection_id,
            payload,
        )

        return self._client.post(
            endpoint=actual_endpoint,
            body=payload,
            raise_on_error=raise_on_error,
        )

    def get_by_classification_project(self, project_id: int, query: dict = None) -> T:
        """
        Retrieve collections associated with a classification project.

        Parameters
        ----------
        project_id : int
            The ID of the classification project.

        Returns
        -------
        Schemas.TrapperCollectionList
            Collections associated with the specified classification project.
        """
        endpoint = f"/media_classification/api/project/{project_id}/collections"
        res = self._client.get_all_pages(endpoint, query)
        return self._schema(**res)
