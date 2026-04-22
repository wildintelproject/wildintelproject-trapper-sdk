"""
Component for the /api/locations/ resource.
"""

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import Location, LocationExport


class LocationsComponent(TrapperComponent[Location]):
    """
    Component for the ``/geomap/api/locations/`` resource.

    Retrieve, filter, and export location data from Trapper.

    Main endpoints:
    - ``GET /geomap/api/locations``: (listado, paginado y filtrable por query params)
    - ``GET /geomap/api/locations/{id}``: (detalle de una localización)
    - ``GET /geomap/api/locations/export/	``: (exportar a CSV, con filtros por query params)

    **Available filter fields:**

    |------------------|-------------|-------------|
    | Parameter        | Type        | Description |
    |------------------|-------------|-------------|
    | name	           | string      | Partial search (case-insensitive) contains on location name
    | description      | string      | Partial search (case-insensitive) contains on description
    | owner	           | boolean     | true = only locations owned by the current user
    | owners	       | list of PKs | Filter by one or more users (by PK)
    | research_project | list of PKs | Filter by one or more research projects (by PK)
    | locations_map	   | list of PKs | Filter by locations associated to a map
    | deployments	   | list of PKs | Filter locations that have those deployments
    | search           | string      | Global text search across location_id, name, description, county, city, owner username

    **Examples:**

        # Retrieve all locations
        for loc in client.locations.all():
            print(loc)

        # Filter by research project
        for loc in client.locations.where(research_project=1):
            print(loc)

        # Filter by owner and search text
        for loc in client.locations.where(owner=True, search="camera"):
            print(loc)

        # Export all locations to CSV
        client.locations.export(file="/tmp/locations.csv")

        # Export filtered results to CSV
        client.locations.export(query={"research_project": 5}, file="/tmp/project5_locations.csv")
    """

    endpoint = "/geomap/api/locations"
    export_endpoint = "/geomap/api/locations/export/"
    schema = Location
    export_schema = LocationExport
