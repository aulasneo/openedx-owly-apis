"""
Custom DRF permissions for Open edX roles.

- IsCourseCreator: requiere que el usuario sea creador de cursos (global u org)
- IsCourseStaff: requiere que el usuario sea staff/instructor/limited_staff del curso

Se intenta resolver el contexto (curso/org) desde query params o body.
"""
from typing import Optional

from rest_framework.permissions import BasePermission

from opaque_keys.edx.keys import CourseKey, UsageKey
from common.djangoapps.student.roles import (
    CourseStaffRole,
    CourseInstructorRole,
    CourseLimitedStaffRole,
)
from common.djangoapps.student.auth import user_has_role, CourseCreatorRole, OrgContentCreatorRole


def _get_course_key_from_request(request) -> Optional[CourseKey]:
    """Extrae CourseKey desde course_id o vertical_id en query/body."""
    course_id = request.query_params.get("course_id") or request.data.get("course_id")
    if course_id:
        try:
            return CourseKey.from_string(course_id)
        except Exception:  # pylint: disable=broad-except
            return None

    # Intentar desde vertical_id (u otros usage keys)
    usage_id = (
        request.query_params.get("vertical_id")
        or request.data.get("vertical_id")
        or request.query_params.get("usage_id")
        or request.data.get("usage_id")
        or request.query_params.get("block_id")
        or request.data.get("block_id")
    )
    if usage_id:
        try:
            usage_key = UsageKey.from_string(usage_id)
            # Algunos usage keys exigen .course_key
            return getattr(usage_key, "course_key", None)
        except Exception:  # pylint: disable=broad-except
            return None
    return None


def _get_org_from_request(request, fallback_course_key: Optional[CourseKey]) -> Optional[str]:
    """Obtiene org de query/body o del course_key si está disponible."""
    org = request.query_params.get("org") or request.data.get("org")
    if org:
        return org
    if fallback_course_key is not None:
        return getattr(fallback_course_key, "org", None)
    return None


class IsCourseCreator(BasePermission):
    message = "User must be a Course Creator"

    def has_permission(self, request, view) -> bool:  # noqa: D401
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        course_key = _get_course_key_from_request(request)
        org = _get_org_from_request(request, course_key)

        # CourseCreator global
        if user_has_role(user, CourseCreatorRole()):
            return True
        # Por organización (si se proporciona o se puede inferir)
        if org:
            return user_has_role(user, OrgContentCreatorRole(org=org))
        return False


class IsCourseStaff(BasePermission):
    message = "User must be Course Staff for the specified course"

    def has_permission(self, request, view) -> bool:  # noqa: D401
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        course_key = _get_course_key_from_request(request)
        if course_key is None:
            # No hay forma de validar staff de curso sin contexto del curso
            return False

        return (
            CourseInstructorRole(course_key).has_user(user)
            or CourseStaffRole(course_key).has_user(user)
            or CourseLimitedStaffRole(course_key).has_user(user)
        )


class IsAdminOrCourseCreator(BasePermission):
    """Permite acceso a admin (superuser o staff) o a Course Creator."""

    message = "User must be admin or Course Creator"

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        # Bypass para administradores del sitio Open edX
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        return IsCourseCreator().has_permission(request, view)


class IsAdminOrCourseCreatorOrCourseStaff(BasePermission):
    """Permite acceso a admin, Course Creator o Course Staff (instructor/staff/limited)."""

    message = "User must be admin, Course Creator or Course Staff"

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        # Bypass para administradores del sitio Open edX
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        # OR entre creador de curso y staff del curso
        return (
            IsCourseCreator().has_permission(request, view)
            or IsCourseStaff().has_permission(request, view)
        )
