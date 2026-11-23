"""``wait_for_import()``: wait for an asynchronous import to land, by looking at the API."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.components.locations import LocationsComponent


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("trapper_client.components.base.time.sleep", lambda s: None)


def component(cls, attr, visible_after: int, ids):
    """A component whose ``where(search=id)`` shows ``ids`` only from poll number ``visible_after``."""
    comp = cls(MagicMock())
    calls = {"n": 0}

    def where(search, page_size):
        calls["n"] += 1
        if calls["n"] < visible_after:
            return []
        return [SimpleNamespace(**{attr: search})] if search in ids else []

    comp.where = where
    return comp, calls


@pytest.mark.parametrize("cls,attr,method,ids", [
    (LocationsComponent, "location_id", "wait_for_import", ["a", "b"]),
    (DeploymentsComponent, "deployment_id", "wait_for_import", ["x"]),
])
def test_returns_true_once_every_id_is_visible(cls, attr, method, ids):
    comp, calls = component(cls, attr, visible_after=3, ids=ids)

    assert getattr(comp, method)(ids, timeout=60, interval=0) is True
    assert calls["n"] >= 3


def test_raises_naming_the_missing_ids():
    comp, _ = component(LocationsComponent, "location_id", visible_after=1, ids=["a"])

    with pytest.raises(TimeoutError, match="b"):
        comp.wait_for_import(["a", "b"], timeout=0, interval=0)


def test_returns_false_when_asked_not_to_raise():
    comp, _ = component(LocationsComponent, "location_id", visible_after=1, ids=[])

    assert comp.wait_for_import(["a"], timeout=0, interval=0, raise_on_timeout=False) is False


def test_search_hit_that_is_only_a_partial_match_does_not_count():
    comp = LocationsComponent(MagicMock())
    comp.where = lambda search, page_size: [SimpleNamespace(location_id="don-01-extra")]

    assert comp.wait_for_import(["don-01"], timeout=0, interval=0, raise_on_timeout=False) is False
