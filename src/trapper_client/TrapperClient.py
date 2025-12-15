import sys

from typing import TypeVar
from urllib.parse import urlparse
import attr, os

from typing import Optional
from pydantic import BaseModel
import csv
import logging

from trapper_client.APIClientBase import APIClientBase
from trapper_client.components.ClassificatorsComponent import ClassificatorsComponent
from trapper_client.components.HttpUploader import HTTPUploader
from trapper_client.components.ResourcesComponent import ResourcesComponent
from trapper_client.components.CollectionsComponent import CollectionsComponent
from trapper_client.components.LocationsComponent import LocationsComponent
from trapper_client.components.DeploymentsComponent import DeploymentsComponent
from trapper_client.components.ClassificationProjectsComponent import ClassificationProjectsComponent
from trapper_client.components.ResearchProjectsComponent import ResearchProjectsComponent
from trapper_client.components.MediaComponent import MediaComponent
from trapper_client.components.ObservationsComponent import ObservationsComponent, AIObservationsComponent, \
    UserObservationsComponent
from trapper_client.components.PackageComponent import PackagesComponent


T = TypeVar("T")
logger = logging.getLogger(__name__)

def parse_url(url: str):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"URL inválida: {url}")
    return url

@attr.s(auto_attribs=True)
class TrapperClient:
    """
    Main client for interacting with the Trapper API.

    This client wraps around multiple API components (locations, deployments, etc.)
    and manages authentication, requests, and schema validation.

    Attributes
    ----------
    access_token : str
        Authentication token for API access.
    base_url : str
        Base URL of the Trapper API server.
    user_name : str
        Username for authentication.
    user_password : str
        Password for authentication.
    raw : APIClientBase
        Raw API client instance.
    locations : LocationsComponent
        Component for location-related operations.
    deployments : DeploymentsComponent
        Component for deployment-related operations.
    classification_projects : ClassificationProjectsComponent
        Component for classification project operations.
    research_projects : ResearchProjectsComponent
        Component for research project operations.
    resources : ResourcesComponent
        Component for resource-related operations.
    media : MediaComponent
        Component for media-related operations.
    observations : ObservationsComponent
        Component for observation-related operations.
    collections : CollectionsComponent
        Component for collection-related operations.

    """
    access_token: str
    base_url: str = attr.ib(default="https://wildintel-trap.uhu.es", converter=parse_url)
    user_name: str = attr.ib(repr=False, default="me")
    user_password: str = attr.ib(repr=False, default="")

    raw: APIClientBase = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        self.raw: APIClientBase = APIClientBase(
            access_token=self.access_token,
            user_name=self.user_name,
            user_password=self.user_password,
            base_url=self.base_url,
        )

        self.locations: LocationsComponent = LocationsComponent(self.raw)
        self.deployments: DeploymentsComponent = DeploymentsComponent(self.raw)
        self.classification_projects: ClassificationProjectsComponent = ClassificationProjectsComponent(self.raw)
        self.research_projects: ResearchProjectsComponent = ResearchProjectsComponent(self.raw)
        self.resources: ResourcesComponent = ResourcesComponent(self.raw)
        self.media: MediaComponent = MediaComponent(self.raw)
        self.observations: ObservationsComponent = ObservationsComponent(self.raw)
        self.aiobservations: AIObservationsComponent = AIObservationsComponent(self.raw)
        self.userobservations: UserObservationsComponent = UserObservationsComponent(self.raw)
        self.uploaders: HTTPUploader = HTTPUploader(self.raw)


        self.classificators: ClassificatorsComponent = ClassificatorsComponent(self.raw)
        self.collections: CollectionsComponent = CollectionsComponent(self.raw)
        self.packages: PackagesComponent = PackagesComponent(self.raw)

    @classmethod
    def from_environment(cls) -> "TrapperClient":
        """
        Create a TrapperClient instance using environment variables.

        Returns
        -------
        TrapperClient
            A new TrapperClient instance configured from environment variables.

        Environment Variables
        ---------------------
        TRAPPER_ACCESS_TOKEN : str
            Authentication token for API access.
        TRAPPER_URL : str
            Base URL of the Trapper API server.
        TRAPPER_USER_NAME : str
            Username for authentication.
        TRAPPER_USER_PASSWORD : str
            Password for authentication.
        """
        logger.debug("Creating TrapperClient from environment variables.")
        env = os.environ

        logger.debug(f"{env.get("TRAPPER_ACCESS_TOKEN", None)} - {env.get("TRAPPER_URL", None)} - {env.get("TRAPPER_USER_NAME", None)} - {env.get("TRAPPER_USER_PASSWORD", None)}")

        return cls(
            access_token=env.get("TRAPPER_ACCESS_TOKEN", None),
            base_url=env.get("TRAPPER_URL", "https://wildintel-trap.uhu.es"),
            user_name=env.get("TRAPPER_USER_NAME", None),
            user_password=env.get("TRAPPER_USER_PASSWORD", None),
        )

    @staticmethod
    def export_list_to_csv(data_list: BaseModel, output_file: Optional[str] = None,
                           include_pagination: bool = False):
        """
        Export a Pydantic list object with pagination to CSV.

        Parameters
        ----------
        data_list : BaseModel
            Pydantic model containing 'pagination' and 'results' attributes.
        output_file : str, optional
            Optional path to a CSV file. Defaults to stdout.
        include_pagination : bool, optional
            If True, adds pagination fields to each row. Defaults to False.

        Returns
        -------
        str or None
            The output file path if output_file was provided, otherwise None.

        Raises
        ------
        ValueError
            If the provided object doesn't have 'results' and 'pagination' attributes.
        """

        if not hasattr(data_list, "results") or not hasattr(data_list, "pagination"):
            raise ValueError("The provided object must have 'results' and 'pagination' attributes.")
        if not hasattr(data_list, "results") or not hasattr(data_list, "pagination"):
            raise ValueError("The provided object must have 'results' and 'pagination' attributes.")

        results = data_list.results
        if not results:
            print("No data to export.")
            return

        # Base field names from the first result
        fieldnames = [
            field.alias if field.alias else name
            for name, field in type(results[0]).model_fields.items()
        ]

        # Add pagination fields if requested
        if include_pagination:
            pagination_fields = ["page", "page_size", "pages", "count"]
            fieldnames = pagination_fields + fieldnames

        output = open(output_file, "w", newline="", encoding="utf-8") if output_file else sys.stdout
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for item in results:
            row = item.model_dump(by_alias=True)
            if include_pagination:
                row = {**data_list.pagination.model_dump(), **row}
            writer.writerow(row)

        if output_file:
            output.close()

        return output_file