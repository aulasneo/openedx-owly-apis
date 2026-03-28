"""
Open edX role inspection endpoints.

These endpoints report the effective role of the authenticated user in the
requested course or organization context.

Example:
GET /owly-roles/me?course_id=course-v1:ORG+NUM+RUN&org=ORG
"""
from typing import Optional

from common.djangoapps.student.auth import CourseCreatorRole, OrgContentCreatorRole, user_has_role
from common.djangoapps.student.roles import CourseInstructorRole, CourseLimitedStaffRole, CourseStaffRole
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from opaque_keys.edx.keys import CourseKey
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from openedx_owly_apis.views.v1.response_utils import error_response, success_response
from openedx_owly_apis.views.v1.serializers import RolesMeQuerySerializer


class OpenedXRolesViewSet(viewsets.ViewSet):
    """Endpoints for resolving the effective Open edX role of the current user."""
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _validated(data):
        serializer = RolesMeQuerySerializer(data=data)
        if not serializer.is_valid():
            return None, error_response(
                "Validation failed",
                "validation_error",
                details=serializer.errors,
            )
        return serializer.validated_data, None

    @staticmethod
    def _parse_course_key(course_id: Optional[str]):
        if not course_id:
            return None, None
        try:
            return CourseKey.from_string(course_id), None
        except Exception as exc:  # pylint: disable=broad-except
            return None, f"Invalid course_id: {exc}"

    @staticmethod
    def _is_course_staff(user, course_key) -> bool:
        if not course_key:
            return False
        # Considerar instructor, staff y limited_staff como "course staff".
        return (
            CourseInstructorRole(course_key).has_user(user) or
            CourseStaffRole(course_key).has_user(user) or
            CourseLimitedStaffRole(course_key).has_user(user)
        )

    @staticmethod
    def _is_course_creator(user, org: Optional[str]) -> bool:
        # Respeta settings: DISABLE_COURSE_CREATION y ENABLE_CREATOR_GROUP
        if user_has_role(user, CourseCreatorRole()):
            return True
        if org:
            return user_has_role(user, OrgContentCreatorRole(org=org))
        return False

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """
        Return the effective role of the authenticated user.

        Optional query parameters:
        - ``course_id``: evaluate whether the user is course staff for that course
        - ``org``: evaluate whether the user is an organization-scoped course creator
        """
        data, error = self._validated(request.query_params)
        if error:
            return error

        user = request.user
        course_id = data.get("course_id")
        org = data.get("org")

        course_key, course_err = self._parse_course_key(course_id)
        if course_err:
            return error_response(course_err, "invalid_course_id")

        is_authenticated = bool(user and user.is_authenticated)
        is_superadmin = bool(user and (user.is_superuser or user.is_staff))
        is_course_staff = self._is_course_staff(user, course_key)
        is_course_creator = self._is_course_creator(user, org)

        # Determinar rol efectivo por prioridad
        effective = (
            "SuperAdmin" if is_superadmin else
            "CourseStaff" if is_course_staff else
            "CourseCreator" if is_course_creator else
            "Authenticated" if is_authenticated else
            "Anonymous"
        )

        return success_response({
            "username": getattr(user, "username", None),
            "roles": {
                "superadmin": is_superadmin,
                "course_staff": is_course_staff,
                "course_creator": is_course_creator,
                "authenticated": is_authenticated,
            },
            "effective_role": effective,
            "context": {
                "course_id": course_id,
                "org": org,
            }
        })
