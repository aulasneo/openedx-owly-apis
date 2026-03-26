"""Validation helpers for course structure payloads."""


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
                        f"units[{unit_index}].subsections_list[{subsection_index}] must be an object"
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
                        f"units[{unit_index}].subsections_list[{subsection_index}].verticals_list must be a list"
                    ),
                }

            for vertical_index, vertical in enumerate(verticals_list):
                if not isinstance(vertical, dict):
                    return {
                        "success": False,
                        "error": "invalid_units_config",
                        "message": (
                            "units[{0}].subsections_list[{1}].verticals_list[{2}] must be an object"
                        ).format(unit_index, subsection_index, vertical_index),
                    }

                if not vertical.get("name"):
                    return {
                        "success": False,
                        "error": "invalid_units_config",
                        "message": (
                            "units[{0}].subsections_list[{1}].verticals_list[{2}].name is required"
                        ).format(unit_index, subsection_index, vertical_index),
                    }

    return None
