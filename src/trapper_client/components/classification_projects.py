"""
Component for the /api/cs/projects/ (classification projects) resource.
"""
from typing import Dict, Any, Callable

from trapper_client import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationProject, CollectionCP, PaginatedResult


class ClassificationProjectsComponent(TrapperComponent[ClassificationProject]):
    """
    Component for the ``/media_classification/api/projects`` resource.

    Retrieve, filter, and export classification project data from Trapper.

    **Main endpoints:**

    - ``GET /media_classification/api/projects``: (listado, paginado y filtrable por query params)
    -  ``GET /media_classification/api/projects/{id}``: (detalle de un proyecto de clasificación)


    **Available filter fields:**

    |------------------|-------------|-------------|
    | Parameter        | Type        | Description |
    |------------------|-------------|-------------|
    | owner	           | boolean	 | true = projects where user is owner, manager, or has ANY role
    | status	       | choice	     | Filter by project status
    | research_project | PK	         | Filter by research project FK
    | search           | str         | Searches across: name, owner__username, research_project__name


    ** Example:: **

        for proj in client.classification_projects.all():
            print(proj)

        # Export to CSV
        client.classification_projects.export(file="/tmp/cs_projects.csv")
    """

    endpoint = "/media_classification/api/projects"
    schema = ClassificationProject
