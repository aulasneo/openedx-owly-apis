from rest_framework import serializers


class ContentGroupSerializer(serializers.Serializer):
    """
    Serializer for creating and updating content groups.
    
    Since OpenEdX content groups don't use Django models directly,
    we use a Serializer instead of ModelSerializer.
    """
    course_id = serializers.CharField(
        max_length=255,
        help_text="Course identifier (e.g., course-v1:ORG+NUM+RUN)"
    )
    name = serializers.CharField(
        max_length=255,
        help_text="Name of the content group"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description of the content group"
    )

    def validate_course_id(self, value):
        """Validate course_id format"""
        if not value or not value.strip():
            raise serializers.ValidationError("course_id cannot be empty")
        return value.strip()

    def validate_name(self, value):
        """Validate name field"""
        if not value or not value.strip():
            raise serializers.ValidationError("name cannot be empty")
        return value.strip()


class ContentGroupListSerializer(serializers.Serializer):
    """
    Serializer for listing content groups (read-only).
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    course_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, required=False)
    updated_at = serializers.DateTimeField(read_only=True, required=False)


class ContentGroupUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating content groups.
    All fields are optional for partial updates.
    """
    course_id = serializers.CharField(
        max_length=255,
        help_text="Course identifier (e.g., course-v1:ORG+NUM+RUN)"
    )
    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="New name of the content group"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="New description of the content group"
    )

    def validate_course_id(self, value):
        """Validate course_id format"""
        if not value or not value.strip():
            raise serializers.ValidationError("course_id cannot be empty")
        return value.strip()

    def validate_name(self, value):
        """Validate name field"""
        if value is not None and (not value or not value.strip()):
            raise serializers.ValidationError("name cannot be empty")
        return value.strip() if value else value


class CohortAssignmentSerializer(serializers.Serializer):
    """
    Serializer for assigning/unassigning content groups to cohorts.
    """
    course_id = serializers.CharField(
        max_length=255,
        help_text="Course identifier (e.g., course-v1:ORG+NUM+RUN)"
    )
    content_group_id = serializers.IntegerField(
        help_text="ID of the content group"
    )
    cohort_id = serializers.IntegerField(
        help_text="ID of the cohort"
    )

    def validate_course_id(self, value):
        """Validate course_id format"""
        if not value or not value.strip():
            raise serializers.ValidationError("course_id cannot be empty")
        return value.strip()

    def validate_content_group_id(self, value):
        """Validate content_group_id"""
        if value is None or value <= 0:
            raise serializers.ValidationError("content_group_id must be a positive integer")
        return value

    def validate_cohort_id(self, value):
        """Validate cohort_id"""
        if value is None or value <= 0:
            raise serializers.ValidationError("cohort_id must be a positive integer")
        return value
