"""``deployments.wait_for_update()``: wait until an update import shows its values in the export."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.schemas import DeploymentExport


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("trapper_client.components.deployments.time.sleep", lambda s: None)


def row(deployment_id, **values):
    return DeploymentExport.model_validate({"_id": 1, "deploymentID": deployment_id, **values})


def component(states):
    """A component whose export gives, poll after poll, the rows of ``states`` (the last one repeats)."""
    comp = DeploymentsComponent(MagicMock())
    calls = {"n": 0, "search": []}

    def export(file=None, search=None, **kwargs):
        calls["search"].append(search)
        state = states[min(calls["n"], len(states) - 1)]
        calls["n"] += 1
        if isinstance(state, Exception):
            raise state
        return [r for r in state if r.deployment_id.startswith(search)]

    comp.export = export
    return comp, calls


class TestWaitForUpdate:

    def test_true_at_once_when_the_values_are_already_there(self):
        comp, calls = component([[row("d1", cameraHeight="1.25")]])
        assert comp.wait_for_update({"d1": {"camera_height": 1.25}}) is True
        assert calls["n"] == 1

    def test_waits_until_the_values_change(self):
        comp, calls = component([[row("d1", cameraHeight="0.5")], [row("d1", cameraHeight="0.5")],
                                 [row("d1", cameraHeight="1.25")]])
        assert comp.wait_for_update({"d1": {"camera_height": 1.25}}) is True
        assert calls["n"] == 3

    def test_every_field_and_every_deployment_must_match(self):
        comp, _ = component([
            [row("a", cameraHeight="1", habitat="x"), row("b", habitat="y")],
            [row("a", cameraHeight="1", habitat="dehesa"), row("b", habitat="y")],
        ])
        assert comp.wait_for_update({"a": {"camera_height": 1, "habitat": "dehesa"}, "b": {"habitat": "y"}})

    def test_a_deployment_that_is_not_there_yet_is_waited_for(self):
        comp, _ = component([[], [row("d1", habitat="h")]])
        assert comp.wait_for_update({"d1": {"habitat": "h"}}) is True

    def test_an_empty_export_is_a_400_not_an_error(self):
        comp, _ = component([err.BadRequestError("Empty queryset"), [row("d1", habitat="h")]])
        assert comp.wait_for_update({"d1": {"habitat": "h"}}) is True

    def test_other_errors_are_not_hidden(self):
        comp, _ = component([err.ForbiddenError("no")])
        with pytest.raises(err.ForbiddenError):
            comp.wait_for_update({"d1": {"habitat": "h"}})

    def test_numbers_are_compared_with_a_tolerance_and_as_numbers(self):
        comp, _ = component([[row("d1", cameraHeight="0.1")]])
        assert comp.wait_for_update({"d1": {"camera_height": 0.1 + 1e-12}}) is True
        comp, _ = component([[row("d1", cameraHeight="0.1")]])
        assert comp.wait_for_update({"d1": {"camera_height": 0.2}}, timeout=0, raise_on_timeout=False) is False

    def test_none_and_tags_and_texts(self):
        comp, _ = component([[row("d1", deploymentTags="a | b", habitat="")]])
        assert comp.wait_for_update({"d1": {"tags": ["a", "b"]}}) is True
        assert comp.wait_for_update({"d1": {"camera_height": None}}) is True

    def test_timeout_raises_and_names_the_ids(self):
        comp, _ = component([[row("d1", habitat="old")]])
        with pytest.raises(TimeoutError, match="d1"):
            comp.wait_for_update({"d1": {"habitat": "new"}}, timeout=0)

    def test_timeout_can_return_false(self):
        comp, _ = component([[row("d1", habitat="old")]])
        assert comp.wait_for_update({"d1": {"habitat": "new"}}, timeout=0, raise_on_timeout=False) is False

    def test_it_searches_for_each_id(self):
        comp, calls = component([[row("a", habitat="x"), row("b", habitat="y")]])
        comp.wait_for_update({"a": {"habitat": "x"}, "b": {"habitat": "y"}})
        assert calls["search"] == ["a", "b"]

    def test_an_exact_id_is_required(self):
        """Searching 'd1' also finds 'd10': only the exact deployment counts."""
        comp, _ = component([[row("d10", habitat="x")]])
        assert comp.wait_for_update({"d1": {"habitat": "x"}}, timeout=0, raise_on_timeout=False) is False

    def test_nothing_to_wait_for(self):
        comp, calls = component([[]])
        assert comp.wait_for_update({}) is True and calls["n"] == 0

    def test_an_unknown_field_is_refused_before_any_request(self):
        comp, calls = component([[]])
        with pytest.raises(ValueError, match="cameraHeight|camera_hight"):
            comp.wait_for_update({"d1": {"camera_hight": 1}})
        assert calls["n"] == 0
