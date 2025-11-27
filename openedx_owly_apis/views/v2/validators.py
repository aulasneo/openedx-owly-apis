"""
Custom validators for the v2 API endpoints.

This module contains custom validation logic for grades and other v2 API functionality.
"""
import re
from typing import Any, Dict

from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework import serializers

# Handle InvalidKeyError import for different environments
try:
    from opaque_keys import InvalidKeyError
except ImportError:
    # Fallback for testing environments where opaque_keys might not be fully available
    class InvalidKeyError(Exception):
        pass


def validate_course_id(course_id: str) -> str:
    """
    Validate that the course_id is a valid OpenEdX course identifier.

    Args:
        course_id (str): Course identifier to validate

    Returns:
        str: Validated course_id

    Raises:
        serializers.ValidationError: If course_id is invalid
    """
    if not course_id:
        raise serializers.ValidationError("Course ID cannot be empty")

    try:
        CourseKey.from_string(course_id)
    except InvalidKeyError:
        raise serializers.ValidationError(
            f"Invalid course ID format: {course_id}. "
            "Expected format: course-v1:ORG+COURSE+RUN"
        )

    return course_id


def validate_unit_id(unit_id: str) -> str:
    """
    Validate that the unit_id is a valid OpenEdX usage key.

    Args:
        unit_id (str): Unit identifier to validate

    Returns:
        str: Validated unit_id

    Raises:
        serializers.ValidationError: If unit_id is invalid
    """
    if not unit_id:
        raise serializers.ValidationError("Unit ID cannot be empty")

    try:
        UsageKey.from_string(unit_id)
    except InvalidKeyError:
        raise serializers.ValidationError(
            f"Invalid unit ID format: {unit_id}. "
            "Expected format: block-v1:ORG+COURSE+RUN+type@TYPE+block@BLOCK"
        )

    return unit_id


def validate_username(username: str) -> str:
    """
    Validate that the username follows OpenEdX username conventions.

    Args:
        username (str): Username to validate

    Returns:
        str: Validated username

    Raises:
        serializers.ValidationError: If username is invalid
    """
    if not username:
        raise serializers.ValidationError("Username cannot be empty")

    if len(username) < 2:
        raise serializers.ValidationError("Username must be at least 2 characters long")

    if len(username) > 150:
        raise serializers.ValidationError("Username cannot exceed 150 characters")

    # Check for valid characters (alphanumeric, underscore, hyphen, dot)
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        raise serializers.ValidationError(
            "Username can only contain letters, numbers, underscores, hyphens, and dots"
        )

    return username


def validate_grade_range(grade_value: float, max_grade: float) -> Dict[str, float]:
    """
    Validate that grade values are within acceptable ranges.

    Args:
        grade_value (float): The grade value
        max_grade (float): The maximum possible grade

    Returns:
        Dict[str, float]: Dictionary with validated grade_value and max_grade

    Raises:
        serializers.ValidationError: If grade values are invalid
    """
    if grade_value < 0:
        raise serializers.ValidationError("Grade value cannot be negative")

    if max_grade <= 0:
        raise serializers.ValidationError("Maximum grade must be greater than 0")

    if grade_value > max_grade:
        raise serializers.ValidationError(
            f"Grade value ({grade_value}) cannot exceed maximum grade ({max_grade})"
        )

    # Check for reasonable upper limits
    if max_grade > 10000:
        raise serializers.ValidationError("Maximum grade cannot exceed 10,000")

    return {
        'grade_value': grade_value,
        'max_grade': max_grade
    }


def validate_comment_length(comment: str) -> str:
    """
    Validate comment length and content.

    Args:
        comment (str): Comment to validate

    Returns:
        str: Validated comment

    Raises:
        serializers.ValidationError: If comment is invalid
    """
    if comment is None:
        return ""

    if len(comment) > 1000:
        raise serializers.ValidationError("Comment cannot exceed 1000 characters")

    # Strip whitespace
    comment = comment.strip()

    return comment


def validate_pagination_params(page: int, page_size: int) -> Dict[str, int]:
    """
    Validate pagination parameters.

    Args:
        page (int): Page number
        page_size (int): Number of items per page

    Returns:
        Dict[str, int]: Dictionary with validated page and page_size

    Raises:
        serializers.ValidationError: If pagination parameters are invalid
    """
    if page < 1:
        raise serializers.ValidationError("Page number must be 1 or greater")

    if page_size < 1:
        raise serializers.ValidationError("Page size must be 1 or greater")

    if page_size > 100:
        raise serializers.ValidationError("Page size cannot exceed 100")

    return {
        'page': page,
        'page_size': page_size
    }


class GradeValidationMixin:
    """
    Mixin class that provides grade validation methods for serializers.
    """

    def validate_course_id(self, value: str) -> str:
        """Validate course_id field."""
        return validate_course_id(value)

    def validate_unit_id(self, value: str) -> str:
        """Validate unit_id field."""
        return validate_unit_id(value)

    def validate_student_username(self, value: str) -> str:
        """Validate student_username field."""
        return validate_username(value)

    def validate_comment(self, value: str) -> str:
        """Validate comment field."""
        return validate_comment_length(value)

    def validate_grade_values(self, grade_value: float, max_grade: float) -> Dict[str, float]:
        """Validate grade value ranges."""
        return validate_grade_range(grade_value, max_grade)


def validate_bulk_grade_data(grades_data: list) -> list:
    """
    Validate bulk grade data for batch operations.

    Args:
        grades_data (list): List of grade dictionaries

    Returns:
        list: Validated grades data

    Raises:
        serializers.ValidationError: If bulk data is invalid
    """
    if not isinstance(grades_data, list):
        raise serializers.ValidationError("Grades data must be a list")

    if len(grades_data) == 0:
        raise serializers.ValidationError("Grades data cannot be empty")

    if len(grades_data) > 100:
        raise serializers.ValidationError("Cannot process more than 100 grades at once")

    validated_grades = []

    for i, grade_data in enumerate(grades_data):
        if not isinstance(grade_data, dict):
            raise serializers.ValidationError(f"Grade data at index {i} must be a dictionary")

        required_fields = ['course_id', 'student_username', 'unit_id', 'grade_value', 'max_grade']
        for field in required_fields:
            if field not in grade_data:
                raise serializers.ValidationError(f"Missing required field '{field}' at index {i}")

        # Validate individual fields
        try:
            validated_grade = {
                'course_id': validate_course_id(grade_data['course_id']),
                'student_username': validate_username(grade_data['student_username']),
                'unit_id': validate_unit_id(grade_data['unit_id']),
                'comment': validate_comment_length(grade_data.get('comment', ''))
            }

            # Validate grade values together
            grade_values = validate_grade_range(
                float(grade_data['grade_value']),
                float(grade_data['max_grade'])
            )
            validated_grade.update(grade_values)

            validated_grades.append(validated_grade)

        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(f"Invalid data type at index {i}: {str(e)}")
        except serializers.ValidationError as e:
            raise serializers.ValidationError(f"Validation error at index {i}: {str(e)}")

    return validated_grades


def validate_grade_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate grade filtering parameters.

    Args:
        filters (Dict[str, Any]): Filter parameters

    Returns:
        Dict[str, Any]: Validated filters

    Raises:
        serializers.ValidationError: If filters are invalid
    """
    validated_filters = {}

    # Validate course_id if provided
    if 'course_id' in filters and filters['course_id']:
        validated_filters['course_id'] = validate_course_id(filters['course_id'])

    # Validate student_username if provided
    if 'student_username' in filters and filters['student_username']:
        validated_filters['student_username'] = validate_username(filters['student_username'])

    # Validate unit_id if provided
    if 'unit_id' in filters and filters['unit_id']:
        validated_filters['unit_id'] = validate_unit_id(filters['unit_id'])

    # Validate grade range filters
    if 'min_grade' in filters and filters['min_grade'] is not None:
        min_grade = float(filters['min_grade'])
        if min_grade < 0:
            raise serializers.ValidationError("Minimum grade filter cannot be negative")
        validated_filters['min_grade'] = min_grade

    if 'max_grade_filter' in filters and filters['max_grade_filter'] is not None:
        max_grade_filter = float(filters['max_grade_filter'])
        if max_grade_filter < 0:
            raise serializers.ValidationError("Maximum grade filter cannot be negative")
        validated_filters['max_grade_filter'] = max_grade_filter

    # Validate that min_grade <= max_grade_filter if both are provided
    if ('min_grade' in validated_filters and 'max_grade_filter' in validated_filters):
        if validated_filters['min_grade'] > validated_filters['max_grade_filter']:
            raise serializers.ValidationError(
                "Minimum grade filter cannot be greater than maximum grade filter"
            )

    # Validate pagination
    if 'page' in filters or 'page_size' in filters:
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        pagination = validate_pagination_params(page, page_size)
        validated_filters.update(pagination)

    return validated_filters
