"""
Unit tests for ClassificationPackageComponent.get_project_package().

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.classification_package import ClassificationPackageComponent
from trapper_client.schemas import ResultsDataPackageResponse

PROJECT_PK = 7


@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return ClassificationPackageComponent(client)


def _mock_response(client, payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    client.make_request.return_value = response
    return response


class TestGetProjectPackage:

    def test_uses_correct_endpoint_and_query(self, component, client):
        _mock_response(client, {"data": {"message": "ok", "errors": None, "package": None}})

        component.get_project_package(project_pk=PROJECT_PK, clear_cache=True)

        call = client.make_request.call_args
        assert call.kwargs["endpoint"] == f"media_classification/api/package/{PROJECT_PK}/"
        assert call.kwargs["method"] == "GET"
        assert call.kwargs["query"]["clear_cache"] is True

    def test_always_calls_make_request_with_raise_on_error_false(self, component, client):
        """This endpoint's error body is {"data": {...}}, not the generic
        {"_error": {...}} shape APIClientBase._handle_error expects — letting
        it auto-raise would surface the raw dict repr instead of the
        server's real message. So make_request is always called with
        raise_on_error=False, regardless of what the caller passes."""
        _mock_response(client, {"data": {}})

        component.get_project_package(project_pk=PROJECT_PK, raise_on_error=True)
        assert client.make_request.call_args.kwargs["raise_on_error"] is False

        component.get_project_package(project_pk=PROJECT_PK, raise_on_error=False)
        assert client.make_request.call_args.kwargs["raise_on_error"] is False

    def test_returns_validated_response_on_success(self, component, client):
        payload = {"data": {"message": "ok", "errors": None, "package": "https://example.com/pkg.zip"}}
        _mock_response(client, payload)

        result = component.get_project_package(project_pk=PROJECT_PK)

        assert isinstance(result, ResultsDataPackageResponse)
        assert result.data.package == "https://example.com/pkg.zip"

    def test_returns_unvalidated_model_when_validate_false(self, component, client):
        """validate=False still builds a ResultsDataPackageResponse (via
        model_construct, skipping validation) rather than a plain dict —
        note "data" itself stays an unvalidated raw dict too, since
        model_construct never instantiates nested models."""
        payload = {"data": {"message": "ok", "errors": None, "package": "https://example.com/pkg.zip"}}
        _mock_response(client, payload)

        result = component.get_project_package(project_pk=PROJECT_PK, validate=False)

        assert isinstance(result, ResultsDataPackageResponse)
        assert result.data == {"message": "ok", "errors": None, "package": "https://example.com/pkg.zip"}

    def test_raises_clean_error_with_message_and_errors_on_400(self, component, client):
        """Regression: the server's real data.message/data.errors must appear
        in the exception, not a stringified {'data': {...}} dict repr."""
        _mock_response(
            client,
            {"data": {
                "message": "Bad request",
                "errors": "'NoneType' object has no attribute 'get_download_url'",
                "package": None,
            }},
            status_code=400,
        )

        with pytest.raises(err.BadRequestError) as exc_info:
            component.get_project_package(project_pk=PROJECT_PK)

        message = str(exc_info.value)
        assert "Bad request" in message
        assert "get_download_url" in message
        # The old bug: the raw dict repr (with the "data" key) leaking through.
        assert "{'data'" not in message

    def test_maps_404_to_not_found_error(self, component, client):
        _mock_response(
            client,
            {"data": {"message": "Project not found", "errors": None, "package": None}},
            status_code=404,
        )

        with pytest.raises(err.NotFoundError, match="Project not found"):
            component.get_project_package(project_pk=PROJECT_PK)

    def test_returns_payload_without_raising_when_raise_on_error_false(self, component, client):
        payload = {"data": {"message": "Bad request", "errors": {"project": ["invalid"]}, "package": None}}
        _mock_response(client, payload, status_code=400)

        result = component.get_project_package(project_pk=PROJECT_PK, raise_on_error=False)

        assert result == payload

    def test_raises_clear_error_instead_of_crashing_on_non_json_500(self, component, client):
        """A genuine unhandled server error (HTML page, not JSON) must not
        crash with a raw JSONDecodeError."""
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        response.text = "<!DOCTYPE html><html><body><h1>Oops, Server error</h1></body></html>"
        client.make_request.return_value = response

        with pytest.raises(err.ServerError) as exc_info:
            component.get_project_package(project_pk=PROJECT_PK)

        message = str(exc_info.value)
        assert "non-JSON response" in message
        assert "Oops, Server error" in message

    def test_returns_synthesized_dict_on_non_json_500_when_raise_on_error_false(self, component, client):
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError("bad json")
        response.text = "<html>server error</html>"
        client.make_request.return_value = response

        result = component.get_project_package(project_pk=PROJECT_PK, raise_on_error=False)

        assert "server error" in result["data"]["message"]
        assert result["data"]["errors"] is None
        assert result["data"]["package"] is None

    def test_raises_clear_error_when_success_status_has_non_json_body(self, component, client):
        response = MagicMock()
        response.status_code = 200
        response.json.side_effect = ValueError("bad json")
        response.text = "<html>not json</html>"
        client.make_request.return_value = response

        with pytest.raises(err.APIError, match="isn't JSON"):
            component.get_project_package(project_pk=PROJECT_PK)
