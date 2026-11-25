"""
A non-JSON error answer is reported in a few words (issue #123). No server needed.
"""
from __future__ import annotations

import httpx
import pytest

from trapper_client import err
from trapper_client.trapper_client import TrapperClient


def _client(handler):
    client = TrapperClient(base_url="http://trapper.test", access_token="t", trapper_version="v2")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_an_html_page_is_its_title_and_the_request():
    page = "<!doctype html><html><head><title>Server Error (500)</title></head><body>" + "x" * 5000 + "</body></html>"
    client = _client(lambda request: httpx.Response(500, text=page, headers={"content-type": "text/html"}))
    with pytest.raises(err.ServerError) as caught:
        client.get("media_classification/api/sequences", query={"search": "x"})
    message = str(caught.value)
    assert message.startswith("an HTML page: Server Error (500) (GET http://trapper.test/")
    assert "search=x" in message and len(message) < 300


def test_plain_text_is_cut():
    client = _client(lambda request: httpx.Response(502, text="bad gateway " * 100))
    with pytest.raises(err.APIError) as caught:
        client.get("x")
    assert "..." in str(caught.value) and len(str(caught.value)) < 400


def test_json_errors_are_kept():
    client = _client(lambda request: httpx.Response(400, json={"species": ["Select a valid choice."]}))
    with pytest.raises(err.BadRequestError, match="Select a valid choice"):
        client.get("x")
