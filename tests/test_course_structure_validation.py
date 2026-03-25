def test_create_course_structure_validation_rejects_sections_shape():
    from openedx_owly_apis.operations.courses import _validate_course_structure_payload

    result = _validate_course_structure_payload(
        {
            "sections": [
                {
                    "display_name": "Week 1",
                }
            ]
        }
    )

    assert result["success"] is False
    assert result["error"] == "invalid_units_config"
    assert "units_config.units" in result["message"]


def test_create_course_structure_validation_accepts_supported_shape():
    from openedx_owly_apis.operations.courses import _validate_course_structure_payload

    result = _validate_course_structure_payload(
        {
            "units": [
                {
                    "name": "Week 1",
                    "subsections_list": [
                        {
                            "name": "Introduction",
                            "verticals_list": [
                                {"name": "Welcome"},
                            ],
                        }
                    ],
                }
            ]
        }
    )

    assert result is None


def test_create_course_structure_validation_requires_names():
    from openedx_owly_apis.operations.courses import _validate_course_structure_payload

    result = _validate_course_structure_payload(
        {
            "units": [
                {
                    "name": "Week 1",
                    "subsections_list": [
                        {
                            "verticals_list": [
                                {"name": "Welcome"},
                            ],
                        }
                    ],
                }
            ]
        }
    )

    assert result["success"] is False
    assert result["error"] == "invalid_units_config"
    assert "name is required" in result["message"]
