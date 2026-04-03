"""Request/query serializers for v1 Open edX Owly APIs."""

from rest_framework import serializers

from openedx_owly_apis.operations.course_structure_validation import validate_course_structure_payload
from openedx_owly_apis.views.v2.validators import validate_course_id, validate_unit_id


def _validate_usage_key(value: str) -> str:
    return validate_unit_id(value)


class CourseIdSerializerMixin:
    def validate_course_id(self, value):
        return validate_course_id(value)


class UsageKeySerializerMixin:
    def validate_vertical_id(self, value):
        return _validate_usage_key(value)

    def validate_unit_locator(self, value):
        return _validate_usage_key(value)

    def validate_block_id(self, value):
        return _validate_usage_key(value)

    def validate_content_id(self, value):
        return _validate_usage_key(value)

    def validate_unit_id(self, value):
        return _validate_usage_key(value)

    def validate_ora_location(self, value):
        return _validate_usage_key(value)

    def validate_starting_block_id(self, value):
        return _validate_usage_key(value)

    def validate_search_id(self, value):
        return _validate_usage_key(value)


class CreateCourseRequestSerializer(serializers.Serializer):
    org = serializers.CharField(max_length=255)
    course_number = serializers.CharField(max_length=255)
    run = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    start_date = serializers.CharField(required=False, allow_blank=False)


class RerunCourseRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    run = serializers.CharField(max_length=255)
    display_name = serializers.CharField(required=False, max_length=255)
    start_date = serializers.CharField(required=False, allow_blank=False)
    end_date = serializers.CharField(required=False, allow_blank=False)
    org = serializers.CharField(required=False, max_length=255)
    course_number = serializers.CharField(required=False, max_length=255)
    background = serializers.BooleanField(required=False, default=True)


class CourseStructureRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    units_config = serializers.JSONField()
    edit = serializers.BooleanField(required=False, default=False)

    def validate_units_config(self, value):
        error = validate_course_structure_payload(value)
        if error:
            raise serializers.ValidationError(error.get("message", "Invalid units_config"))
        return value


class CourseTreeQuerySerializer(serializers.Serializer, CourseIdSerializerMixin, UsageKeySerializerMixin):
    course_id = serializers.CharField()
    starting_block_id = serializers.CharField(required=False)
    depth = serializers.IntegerField(required=False, min_value=0)
    search_id = serializers.CharField(required=False)
    search_type = serializers.CharField(required=False)
    search_name = serializers.CharField(required=False)
    content_branch = serializers.ChoiceField(
        required=False,
        default="published_preferred",
        choices=["draft", "published", "published_preferred"],
    )


class UnitContentsQuerySerializer(serializers.Serializer, CourseIdSerializerMixin, UsageKeySerializerMixin):
    course_id = serializers.CharField()
    vertical_id = serializers.CharField()
    content_branch = serializers.ChoiceField(
        required=False,
        default="published_preferred",
        choices=["draft", "published", "published_preferred"],
    )


class HtmlContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    vertical_id = serializers.CharField()
    html_config = serializers.JSONField()


class VideoContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    vertical_id = serializers.CharField()
    video_config = serializers.JSONField()


class ProblemContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    vertical_id = serializers.CharField()
    problem_config = serializers.JSONField()


class DiscussionContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    vertical_id = serializers.CharField()
    discussion_config = serializers.JSONField()


class UpdateCourseSettingsRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    settings_data = serializers.JSONField(required=False, default=dict)


class UpdateAdvancedSettingsRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    advanced_settings = serializers.JSONField(required=False, default=dict)


class ConfigureCertificatesRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    certificate_config = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False)


class ControlUnitAvailabilityRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    unit_id = serializers.CharField()
    availability_config = serializers.JSONField(required=False, default=dict)


class ProblemChoiceSerializer(serializers.Serializer):
    text = serializers.CharField()
    correct = serializers.BooleanField()


class ProblemDataSerializer(serializers.Serializer):
    question_text = serializers.CharField(required=False)
    choices = ProblemChoiceSerializer(many=True, required=False)
    correct_answer = serializers.CharField(required=False)
    tolerance = serializers.CharField(required=False)
    case_sensitive = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object for problem_data.")

        allowed_fields = set(self.fields.keys())
        unknown_fields = sorted(set(data.keys()) - allowed_fields)
        if unknown_fields:
            raise serializers.ValidationError(
                {
                    field: ["Unknown field."]
                    for field in unknown_fields
                }
            )

        return super().to_internal_value(data)


class CreateProblemComponentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    unit_locator = serializers.CharField()
    problem_type = serializers.ChoiceField(
        choices=[
            "multiplechoiceresponse",
            "choiceresponse",
            "optionresponse",
            "numericalresponse",
            "stringresponse",
        ],
        required=False,
        default="multiplechoiceresponse",
    )
    display_name = serializers.CharField(required=False, default="New Problem")
    problem_data = ProblemDataSerializer(required=False, default=dict)


class PublishContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    content_id = serializers.CharField()
    publish_type = serializers.ChoiceField(
        choices=["auto", "course", "unit"],
        required=False,
        default="auto",
    )

    def validate_content_id(self, value):
        try:
            return validate_course_id(value)
        except serializers.ValidationError:
            return _validate_usage_key(value)


class DeleteXBlockRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    block_id = serializers.CharField()


class ManageCourseStaffRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    user_identifier = serializers.CharField()
    action = serializers.ChoiceField(choices=["add", "remove"])
    role_type = serializers.ChoiceField(choices=["staff", "course_creator"], required=False, default="staff")


class ListCourseStaffQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    role_type = serializers.ChoiceField(
        choices=["staff", "course_creator"],
        required=False,
    )


class OraContentRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    vertical_id = serializers.CharField()
    ora_config = serializers.JSONField()


class OraGradeRequestSerializer(serializers.Serializer, UsageKeySerializerMixin):
    ora_location = serializers.CharField()
    student_username = serializers.CharField(required=False)
    submission_uuid = serializers.CharField(required=False)
    grade_data = serializers.JSONField(required=False)
    options_selected = serializers.JSONField(required=False)
    criterion_feedback = serializers.JSONField(required=False, default=dict)
    overall_feedback = serializers.CharField(required=False, allow_blank=True, default="")
    assess_type = serializers.CharField(required=False, default="full-grade")

    def validate(self, attrs):
        student_username = attrs.get("student_username")
        submission_uuid = attrs.get("submission_uuid")
        if not student_username and not submission_uuid:
            raise serializers.ValidationError(
                "Either student_username or submission_uuid is required."
            )
        return attrs


class OraLocationQuerySerializer(serializers.Serializer, UsageKeySerializerMixin):
    ora_location = serializers.CharField()


class CreateCohortRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    cohort_name = serializers.CharField(max_length=255)
    assignment_type = serializers.ChoiceField(choices=["manual", "random"], required=False, default="manual")


class CourseIdQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()


class CohortMemberActionRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    cohort_id = serializers.IntegerField(min_value=1)
    user_identifier = serializers.CharField()


class CohortMembersQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    cohort_id = serializers.IntegerField(min_value=1)


class DeleteCohortQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    cohort_id = serializers.IntegerField(min_value=1)


class BulkEmailRequestSerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()
    subject = serializers.CharField(max_length=128)
    body = serializers.CharField()
    targets = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    cohort_id = serializers.IntegerField(required=False, min_value=1)
    schedule = serializers.CharField(required=False)
    template_name = serializers.CharField(required=False)
    from_addr = serializers.EmailField(required=False)


class OverviewAnalyticsQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField(required=False)


class CourseScopedAnalyticsQuerySerializer(serializers.Serializer, CourseIdSerializerMixin):
    course_id = serializers.CharField()


class RolesMeQuerySerializer(serializers.Serializer):
    course_id = serializers.CharField(required=False)
    org = serializers.CharField(required=False)

    def validate_course_id(self, value):
        return validate_course_id(value)
