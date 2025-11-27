from rest_framework import serializers
from typing import Dict, Any
from .validators import GradeValidationMixin, validate_grade_range


class GradeCreateSerializer(serializers.Serializer, GradeValidationMixin):
    """Serializer for creating a new grade."""
    
    course_id = serializers.CharField(
        max_length=255,
        help_text="Course identifier (e.g., course-v1:ORG+NUM+RUN)"
    )
    student_username = serializers.CharField(
        max_length=150,
        help_text="Username of the student to grade"
    )
    unit_id = serializers.CharField(
        max_length=255,
        help_text="Unit/problem identifier to grade"
    )
    grade_value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        help_text="Grade value (e.g., 85.50)"
    )
    max_grade = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        help_text="Maximum possible grade (e.g., 100.00)"
    )
    comment = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Optional comment for the grade"
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that grade_value doesn't exceed max_grade."""
        # Use the validation mixin method
        validated_grades = self.validate_grade_values(
            attrs['grade_value'], 
            attrs['max_grade']
        )
        attrs.update(validated_grades)
        return attrs


class GradeUpdateSerializer(serializers.Serializer, GradeValidationMixin):
    """Serializer for updating an existing grade."""
    
    grade_value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text="New grade value"
    )
    max_grade = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text="New maximum possible grade"
    )
    comment = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Updated comment for the grade"
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that grade_value doesn't exceed max_grade if both are provided."""
        grade_value = attrs.get('grade_value')
        max_grade = attrs.get('max_grade')
        
        if grade_value is not None and max_grade is not None:
            # Use the validation mixin method
            validated_grades = self.validate_grade_values(
                float(grade_value), 
                float(max_grade)
            )
            attrs.update(validated_grades)
        
        return attrs


class GradeResponseSerializer(serializers.Serializer):
    """Serializer for grade response data."""
    
    id = serializers.CharField(read_only=True, help_text="Grade identifier")
    course_id = serializers.CharField(read_only=True, help_text="Course identifier")
    student_username = serializers.CharField(read_only=True, help_text="Student username")
    student_email = serializers.EmailField(read_only=True, help_text="Student email")
    unit_id = serializers.CharField(read_only=True, help_text="Unit identifier")
    unit_name = serializers.CharField(read_only=True, help_text="Unit display name")
    grade_value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Current grade value"
    )
    max_grade = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Maximum possible grade"
    )
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Grade as percentage"
    )
    comment = serializers.CharField(read_only=True, help_text="Grade comment")
    created_at = serializers.DateTimeField(read_only=True, help_text="Creation timestamp")
    updated_at = serializers.DateTimeField(read_only=True, help_text="Last update timestamp")
    graded_by = serializers.CharField(read_only=True, help_text="Username who assigned the grade")


class GradeListQuerySerializer(serializers.Serializer):
    """Serializer for grade list query parameters."""
    
    course_id = serializers.CharField(
        required=False,
        help_text="Filter by course ID"
    )
    student_username = serializers.CharField(
        required=False,
        help_text="Filter by student username"
    )
    unit_id = serializers.CharField(
        required=False,
        help_text="Filter by unit ID"
    )
    min_grade = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Filter by minimum grade value"
    )
    max_grade_filter = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Filter by maximum grade value"
    )
    page = serializers.IntegerField(
        min_value=1,
        required=False,
        default=1,
        help_text="Page number for pagination"
    )
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        default=20,
        help_text="Number of items per page"
    )

