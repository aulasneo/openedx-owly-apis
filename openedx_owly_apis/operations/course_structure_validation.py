"""Validation helpers for course structure payloads."""


def normalize_course_structure_payload(units_config):
    """Return a normalized payload where optional nested lists are always lists."""
    normalized_units = []

    for unit in units_config.get("units", []):
        normalized_unit = dict(unit)
        if (
            "subsections_list" in normalized_unit
            and normalized_unit["subsections_list"] is None
        ):
            normalized_unit["subsections_list"] = []

        normalized_subsections = []
        for subsection in normalized_unit.get("subsections_list") or []:
            normalized_subsection = dict(subsection)
            if (
                "verticals_list" in normalized_subsection
                and normalized_subsection["verticals_list"] is None
            ):
                normalized_subsection["verticals_list"] = []
            normalized_subsections.append(normalized_subsection)

        if "subsections_list" in normalized_unit:
            normalized_unit["subsections_list"] = normalized_subsections

        normalized_units.append(normalized_unit)

    return {
        **units_config,
        "units": normalized_units,
    }


def validate_course_structure_payload(units_config):
    """Validate the supported course structure payload shape."""
    if not isinstance(units_config, dict):
        return {
            "success": False,
            "error": "invalid_units_config",
            "message": "units_config must be an object with a non-empty 'units' list",
        }

    units = units_config.get("units")
    if not isinstance(units, list) or not units:
        return {
            "success": False,
            "error": "invalid_units_config",
            "message": "units_config.units must be a non-empty list",
        }

    for unit_index, unit in enumerate(units):
        if not isinstance(unit, dict):
            return {
                "success": False,
                "error": "invalid_units_config",
                "message": f"units[{unit_index}] must be an object",
            }

        if not unit.get("name"):
            return {
                "success": False,
                "error": "invalid_units_config",
                "message": f"units[{unit_index}].name is required",
            }

        subsections_list = unit.get("subsections_list")
        if subsections_list is None:
            continue

        if not isinstance(subsections_list, list):
            return {
                "success": False,
                "error": "invalid_units_config",
                "message": f"units[{unit_index}].subsections_list must be a list",
            }

        for subsection_index, subsection in enumerate(subsections_list):
            if not isinstance(subsection, dict):
                return {
                    "success": False,
                    "error": "invalid_units_config",
                    "message": (
                        f"units[{unit_index}].subsections_list"
                        f"[{subsection_index}] must be an object"
                    ),
                }

            if not subsection.get("name"):
                return {
                    "success": False,
                    "error": "invalid_units_config",
                    "message": (
                        f"units[{unit_index}].subsections_list[{subsection_index}].name is required"
                    ),
                }

            verticals_list = subsection.get("verticals_list")
            if verticals_list is None:
                continue

            if not isinstance(verticals_list, list):
                return {
                    "success": False,
                    "error": "invalid_units_config",
                    "message": (
                        f"units[{unit_index}].subsections_list"
                        f"[{subsection_index}].verticals_list must be a list"
                    ),
                }

            for vertical_index, vertical in enumerate(verticals_list):
                if not isinstance(vertical, dict):
                    return {
                        "success": False,
                        "error": "invalid_units_config",
                        "message": (
                            f"units[{unit_index}].subsections_list[{subsection_index}]."
                            f"verticals_list[{vertical_index}] must be an object"
                        ),
                    }

                if not vertical.get("name"):
                    return {
                        "success": False,
                        "error": "invalid_units_config",
                        "message": (
                            f"units[{unit_index}].subsections_list[{subsection_index}]."
                            f"verticals_list[{vertical_index}].name is required"
                        ),
                    }

    return None
