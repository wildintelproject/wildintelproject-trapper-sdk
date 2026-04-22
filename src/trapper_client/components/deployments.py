"""
Component for the /api/deployments/ resource.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import Deployment, DeploymentExport


class DeploymentsComponent(TrapperComponent[Deployment]):
    """
    Component for the ``/geomap/api/deployments`` resource.

    **Available endpoints:**

    - ``GET /geomap/api/deployments``: Paginated list of deployments
    - ``GET /geomap/api/deployments/{pk}``: Retrieve a single deployment by ID
    - ``GET /geomap/api/deployments/export/``: Export deployments to CSV (gzipped)

    **Available filter parameters:**

    - ``location`` (int or list): Filter by location ID(s)
    - ``research_project`` (int or list): Filter by research project ID(s)
    - ``tags`` (int or list): Filter by tag ID(s)
    - ``owner`` (bool): Filter by current user ownership (True/False)
    - ``sdate_from``, ``sdate_to`` (date): Filter by start date range (ISO format)
    - ``edate_from``, ``edate_to`` (date): Filter by end date range (ISO format)
    - ``classification_project`` (int): Filter by classification project ID
    - ``collections`` (int or list): Filter by collection ID(s) (via ``colls`` param)
    - ``correct_setup`` (bool): Filter by setup correctness
    - ``correct_tstamp`` (bool): Filter by timestamp correctness
    - ``search`` (str): Search in deployment_id or owner__username

    **Examples:**

        # All deployments in collection 5
        for dep in client.deployments.where(collections=5):
            print(dep)

        # Shortcut: deployments by collection
        for dep in client.deployments.by_collection(5):
            print(dep)

        # Filter by location and date range
        for dep in client.deployments.where(location=42, sdate_from="2024-01-01"):
            print(dep)

        # Export to CSV
        client.deployments.export_by_collection(5, file="/tmp/deps.csv")
    """

    endpoint = "geomap/api/deployments"
    export_endpoint = "geomap/api/deployments/export/"
    schema = Deployment
    export_schema = DeploymentExport

    #def by_collection(
    #    self,
    #    collection_id: int,
    #    query: Dict[str, Any] | None = None,
    #    page_size: int = 50,
    #) -> APIQuery:
    """Return a lazy iterator over deployments filtered by collection.

    Args:
        collection_id: Collection primary key (mapped to ``colls`` param).
        query: Base query parameters.
        page_size: Number of items requested per API page.

    Returns:
        Lazy ``APIQuery`` iterator yielding deployments.
    """
    #    q = dict(query or {})
    #    q["colls"] = collection_id
    #    return APIQuery(client=self.client, endpoint=self.endpoint, query=q, page_size=page_size)

    #def export_by_collection(
    #    self,
    #    collection_id: int,
    #    query: Dict[str, Any] | None = None,
    #    file: str | Path | None = None,
    #) -> Path:
    """Export deployments of a collection to CSV.

    Args:
        collection_id: Collection primary key (mapped to ``colls`` param).
        query: Base query parameters.
        file: Output CSV file path. If ``None``, a temp file is created.

    Returns:
        Path to the generated CSV file.
    """
    #    q = dict(query or {})
    #    q["colls"] = collection_id
    #    return self.export(query=q, file=file)
