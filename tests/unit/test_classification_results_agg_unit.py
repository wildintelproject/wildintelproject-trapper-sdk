"""
Unit tests for ClassificationResultsAggComponent (the trap rates of a classification project).

All API calls are mocked — no real server needed. The rows are the ones Trapper v1/v2 send (checked on both).
"""
from __future__ import annotations

import warnings
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.classification_results_agg import ClassificationResultsAggComponent
from trapper_client.schemas import ClassificationAgg

ROW = {
    "deploymentID": "don01-2024a", "locationID": "don-01", "locationName": "Doñana - Laguna del Sopetón",
    "latitude": "37.0521", "longitude": "-6.4412", "coordinateUncertainty": "10",
    "deploymentStart": "2024-03-01T10:00:00+0100", "deploymentEnd": "2024-04-15T09:30:00+0200", "setupBy": "",
    "cameraID": "CT-1001", "cameraModel": "Reconyx HyperFire 2", "cameraDelay": "", "cameraHeight": "0.45",
    "cameraDepth": "", "cameraTilt": "", "cameraHeading": "", "detectionDistance": "", "timestampIssues": "false",
    "baitUse": "false", "featureType": "", "habitat": "matorral mediterráneo", "deploymentGroups": "",
    "deploymentTags": "spring", "deploymentComments": "Primera campaña", "days": "44", "observationType": "animal",
    "scientificName": "Lynx pardinus", "count": "2", "trapRate": "0.0455",
}

EMPTY = err.BadRequestError('["Empty queryset or you have no permission to access the requested objects."]')


@pytest.fixture
def client():
    c = MagicMock()
    c.server_version = "v2"
    return c


@pytest.fixture
def agg(client):
    return ClassificationResultsAggComponent(client)


class TestRow:

    def test_types(self):
        row = ClassificationAgg.model_validate(ROW)
        assert row.count == 2 and row.days == 44 and row.trapRate == 0.0455
        assert row.latitude == 37.0521 and row.coordinateUncertainty == 10 and row.cameraHeight == 0.45
        assert isinstance(row.deploymentStart, datetime) and row.timestampIssues is False

    def test_empty_cells_are_none(self):
        row = ClassificationAgg.model_validate(ROW)
        assert row.setupBy is None and row.cameraDelay is None and row.countNew is None

    def test_a_deployment_with_no_observation(self):
        row = ClassificationAgg.model_validate({**ROW, "observationType": "", "scientificName": "", "count": "",
                                                "trapRate": ""})
        assert row.scientificName is None and row.count is None and row.trapRate is None


class TestGet:

    def test_rows(self, agg, client):
        client.get.return_value = paginated_response([ROW])
        page = agg.get_project_results_agg(2)
        assert client.get.call_args[0][0] == "media_classification/api/classifications/results/agg/2/"
        assert page.results[0].scientificName == "Lynx pardinus"

    def test_no_rows(self, agg, client):
        client.get.side_effect = EMPTY
        assert agg.get_project_results_agg(2, rdate_from="2030-01-01").results == []

    def test_other_400s_raise(self, agg, client):
        client.get.side_effect = err.BadRequestError('["countNew is not available for this project."]')
        with pytest.raises(err.BadRequestError):
            agg.get_project_results_agg(2, count_var="countNew")

    def test_geojson_is_a_value_error(self, agg):
        with pytest.raises(ValueError, match="get_project_geojson"):
            agg.get_project_results_agg(2, geojson=True)

    def test_approved_is_status_on_v1(self, agg, client):
        client.server_version = "v1"
        client.get.return_value = paginated_response([ROW])
        agg.get_project_results_agg(2, approved=True)
        q = client.get.call_args[1]["query"]
        assert q["status"] is True and "approved" not in q

    @pytest.mark.parametrize("name", ["count_var", "all_dep", "filter_dep", "species", "approved"])
    def test_known_parameters_do_not_warn(self, agg, client, name):
        client.get.return_value = paginated_response([])
        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            agg.get_project_results_agg(2, **{name: "1"})

    def test_unknown_filter_warns(self, agg, client):
        client.get.return_value = paginated_response([])
        with pytest.warns(err.UnknownFilterWarning):
            agg.get_project_results_agg(2, nonsense=1)

    def test_classified_warns_on_v2(self, agg, client):
        client.get.return_value = paginated_response([])
        with pytest.warns(err.UnknownFilterWarning, match="answers 500"):
            agg.get_project_results_agg(2, classified=True)

    def test_classified_does_not_warn_on_v1(self, agg, client):
        client.server_version = "v1"
        client.get.return_value = paginated_response([])
        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            agg.get_project_results_agg(2, classified=True)


class TestGeojson:

    FC = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"count": 2},
                                                     "geometry": {"type": "Point", "coordinates": [-6.44, 37.05]}}]}

    def test_feature_collection(self, agg, client):
        client.get.return_value = paginated_response([self.FC])
        assert agg.get_project_geojson(2, species=3) == self.FC
        assert client.get.call_args[1]["query"]["geojson"] == "True"

    def test_empty(self, agg, client):
        client.get.side_effect = EMPTY
        assert agg.get_project_geojson(2) == {"type": "FeatureCollection", "features": []}


class TestExport:

    def test_rows_to_csv(self, agg, client, tmp_path):
        client.get_all.return_value = paginated_response([ROW])
        out = tmp_path / "agg.csv"
        client._select_file.return_value = out
        assert agg.export_project_results_agg(2, file=out) == out
        rows = client._write_csv.call_args[0][0]
        assert rows[0]["count"] == 2 and rows[0]["trapRate"] == 0.0455

    @pytest.mark.parametrize("flags", [{"raw": True}, {"validate": False}])
    def test_raw(self, agg, client, flags):
        agg.export_project_results_agg(2, file="x.csv", **flags)
        client.export_all.assert_called_once()

    def test_empty_raw_is_an_empty_file(self, agg, client, tmp_path):
        client.export_all.side_effect = EMPTY
        out = tmp_path / "agg.csv"
        client._select_file.return_value = out
        assert agg.export_project_results_agg(2, file=out, raw=True).read_text() == ""

    def test_empty_parsed_is_a_csv_with_no_rows(self, agg, client, tmp_path):
        client.get_all.side_effect = EMPTY
        client._select_file.return_value = tmp_path / "agg.csv"
        agg.export_project_results_agg(2, file=tmp_path / "agg.csv")
        assert client._write_csv.call_args[0][0] == []

    def test_geojson_is_a_value_error(self, agg):
        with pytest.raises(ValueError, match="only supports CSV"):
            agg.export_project_results_agg(2, geojson="true")
