"""``DeploymentExport``: session, array, tags and bait type come from two columns Trapper does name differently."""
from __future__ import annotations

import pytest

from trapper_client.schemas import DeploymentExport


def row(**extra):
    return DeploymentExport.model_validate({"_id": "1", "deploymentID": "d1", **extra})


class TestGroups:

    def test_session_and_array(self):
        r = row(deploymentGroups="session:12 | array:s4")
        assert (r.session, r.array) == ("12", "s4")

    @pytest.mark.parametrize("value, session, array", [
        ("session:12", "12", None),
        ("array:s4", None, "s4"),
        ("array:s4 | session:12", "12", "s4"),       # either order
        ("  session : 12  |  array : s4 ", "12", "s4"),
        ("", None, None),
        ("nonsense", None, None),
        ("other:1 | session:2", "2", None),          # an unknown group is not an error
        ("session:", None, None),
    ])
    def test_forms(self, value, session, array):
        r = row(deploymentGroups=value)
        assert (r.session, r.array) == (session, array)

    def test_a_value_with_a_colon_keeps_the_rest(self):
        assert row(deploymentGroups="session:a:b").session == "a:b"

    def test_the_raw_column_is_not_kept_twice(self):
        assert "deploymentGroups" not in (row(deploymentGroups="session:1").model_extra or {})

    def test_a_value_given_by_name_wins(self):
        assert row(session="mine", deploymentGroups="session:12").session == "mine"


class TestTags:

    def test_tags_are_split(self):
        assert row(deploymentTags="spring | camera trap | x").tags == ["spring", "camera trap", "x"]

    def test_bait_type_is_taken_out_of_the_tags(self):
        r = row(deploymentTags="spring | baitType:Meat")
        assert r.tags == ["spring"] and r.bait_type == "Meat"

    def test_only_a_bait_type(self):
        r = row(deploymentTags="baitType:Fish")
        assert r.tags == [] and r.bait_type == "Fish"

    @pytest.mark.parametrize("value", ["", "  ", " | ", None])
    def test_empty_is_no_tags(self, value):
        r = row(deploymentTags=value)
        assert r.tags == [] and r.bait_type is None

    def test_tags_given_by_name_win(self):
        assert row(tags=["a"], deploymentTags="b").tags == ["a"]

    def test_no_column_no_tags(self):
        r = row()
        assert r.tags == [] and r.session is None and r.array is None and r.bait_type is None

    def test_the_raw_column_is_not_kept_twice(self):
        assert "deploymentTags" not in (row(deploymentTags="a").model_extra or {})

    def test_it_survives_a_round_trip_through_model_dump(self):
        r = row(deploymentGroups="session:1 | array:2", deploymentTags="a | baitType:Meat")
        again = DeploymentExport.model_validate(r.model_dump(mode="json"))
        assert (again.session, again.array, again.tags, again.bait_type) == ("1", "2", ["a"], "Meat")


class TestCameraDepth:

    def test_camera_depth_is_a_number(self):
        assert row(cameraDepth="1.5").camera_depth == 1.5
        assert row(cameraDepth="").camera_depth is None
