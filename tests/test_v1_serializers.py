import pytest

from openedx_owly_apis.views.v1 import serializers as v1_serializers
from openedx_owly_apis.views.v1.serializers import (
    CourseStructureRequestSerializer,
    CreateProblemComponentRequestSerializer,
)


@pytest.fixture(autouse=True)
def bypass_opaque_key_validation(monkeypatch):
    monkeypatch.setattr(v1_serializers, "validate_course_id", lambda value: value)
    monkeypatch.setattr(v1_serializers, "_validate_usage_key", lambda value: value)


def test_course_structure_request_serializer_accepts_supported_units_shape():
    serializer = CourseStructureRequestSerializer(
        data={
            "course_id": "course-v1:TestX+CS101+2024",
            "units_config": {
                "units": [
                    {
                        "name": "Week 1",
                        "subsections_list": [
                            {
                                "name": "Intro",
                                "verticals_list": [{"name": "Welcome"}],
                            }
                        ],
                    }
                ]
            },
            "edit": False,
        }
    )

    assert serializer.is_valid(), serializer.errors


def test_course_structure_request_serializer_rejects_invalid_units_shape():
    serializer = CourseStructureRequestSerializer(
        data={
            "course_id": "course-v1:TestX+CS101+2024",
            "units_config": {"sections": [{"display_name": "Week 1"}]},
        }
    )

    assert not serializer.is_valid()
    assert "units_config" in serializer.errors


def test_create_problem_component_serializer_uses_exact_problem_fields():
    serializer = CreateProblemComponentRequestSerializer(
        data={
            "unit_locator": "block-v1:TestX+CS101+2024+type@vertical+block@unit1",
            "problem_type": "optionresponse",
            "display_name": "Chord Quiz",
            "problem_data": {
                "question_text": "Pick the tonic chord",
                "choices": [
                    {"text": "Cmaj7", "correct": True},
                    {"text": "Dm7", "correct": False},
                ],
            },
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["problem_data"]["question_text"] == "Pick the tonic chord"


def test_create_problem_component_serializer_rejects_unknown_problem_shape():
    serializer = CreateProblemComponentRequestSerializer(
        data={
            "unit_locator": "block-v1:TestX+CS101+2024+type@vertical+block@unit1",
            "problem_type": "optionresponse",
            "problem_data": {
                "question": "Old alias field should not be accepted as contract",
                "choices": [
                    {"text": "Cmaj7", "correct": True},
                ],
            },
        }
    )

    assert not serializer.is_valid()
    assert "problem_data" in serializer.errors
    assert "question" in serializer.errors["problem_data"]
