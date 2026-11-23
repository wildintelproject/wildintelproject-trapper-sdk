"""Unit tests for the choice enumerations of Trapper's forms."""
from __future__ import annotations

import pytest

from trapper_client import AnimalTypes, BaitUse, ClassificatorTemplate, SamplingDesign, SensorMethod


class TestChoice:

    def test_members_are_ints_with_a_label(self):
        assert SamplingDesign.TARGETED == 5
        assert int(SamplingDesign.TARGETED) == 5
        assert SamplingDesign.TARGETED.label == "targeted"
        assert BaitUse.NONE.label == "none"

    @pytest.mark.parametrize("value", [SamplingDesign.TARGETED, 5, "targeted", "TARGETED"])
    def test_parse_accepts_member_number_label_and_name(self, value):
        assert SamplingDesign.parse(value) is SamplingDesign.TARGETED

    @pytest.mark.parametrize("value", [0, 7, True, "nope", "", None, 5.0, [5]])
    def test_parse_rejects_anything_else(self, value):
        with pytest.raises(ValueError, match="sampling_design"):
            SamplingDesign.parse(value, "sampling_design")

    def test_the_error_lists_the_valid_values(self):
        with pytest.raises(ValueError, match=r"scent \(2\), food \(3\)"):
            BaitUse.parse("nope", "bait_use")

    def test_a_member_of_another_enum_is_rejected(self):
        # BaitUse.FOOD is the int 3, which is also SensorMethod.BOTH: do not take one for the other
        with pytest.raises(ValueError, match="another enumeration"):
            SensorMethod.parse(BaitUse.FOOD, "sensor_method")

    @pytest.mark.parametrize("enum, count", [
        (SamplingDesign, 6), (SensorMethod, 3), (AnimalTypes, 3), (BaitUse, 6),
    ])
    def test_numbers_are_consecutive_from_one(self, enum, count):
        assert [m.value for m in enum] == list(range(1, count + 1))


class TestClassificatorTemplate:

    def test_members_are_the_strings_trapper_stores(self):
        assert ClassificatorTemplate.TAB == "tab"
        assert ClassificatorTemplate.TAB.value == "tab" and ClassificatorTemplate.TAB.label == "Tabbed"
        assert ClassificatorTemplate.INLINE.label == "Inline"

    @pytest.mark.parametrize("value", [ClassificatorTemplate.INLINE, "inline", "INLINE", "Inline", " inline "])
    def test_parse_accepts_member_value_label_and_name(self, value):
        assert ClassificatorTemplate.parse(value) is ClassificatorTemplate.INLINE

    @pytest.mark.parametrize("value", ["grid", "", None, 1])
    def test_parse_rejects_anything_else(self, value):
        with pytest.raises(ValueError, match="template.*inline"):
            ClassificatorTemplate.parse(value, "template")
