"""
Custom DRF permissions for Open edX roles.

- IsCourseCreator: requires the user to be a global or org-scoped course creator
- IsCourseStaff: requires the user to be course staff for the relevant course

The permission helpers infer course and organization context from query parameters
or the request body when possible.
"""
from typing import Optional

from common.djangoapps.student.auth import CourseCreatorRole, OrgContentCreatorRole, user_has_role
from common.djangoapps.student.roles import CourseStaffRole
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.permissions import BasePermission


def _get_course_key_from_request(request) -> Optional[CourseKey]:
    """Extract a ``CourseKey`` from ``course_id`` or block identifiers in the request."""
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
    """Extract the organization from the request or fall back to the course key."""
    org = request.query_params.get("org") or request.data.get("org")
    if org:
        return org
    if fallback_course_key is not None:
        return getattr(fallback_course_key, "org", None)
    return None


def is_admin_user(user) -> bool:
    """Return whether the user is a site-level Open edX admin."""
    return bool(
        getattr(user, "is_authenticated", False)
        and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))
    )


def is_course_creator_user(user, org: Optional[str] = None) -> bool:
    """Return whether the user is a global or org-scoped course creator."""
    if not getattr(user, "is_authenticated", False):
        return False

    if user_has_role(user, CourseCreatorRole()):
        return True

    if org:
        return user_has_role(user, OrgContentCreatorRole(org=org))

    return False


def is_course_staff_user(user, course_key: Optional[CourseKey]) -> bool:
    """Return whether the user is course staff for the given course."""
    if not getattr(user, "is_authenticated", False) or course_key is None:
        return False
    return CourseStaffRole(course_key).has_user(user)


class IsCourseCreator(BasePermission):
    message = "User must be a Course Creator"

    def has_permission(self, request, _view) -> bool:  # noqa: D401
        """Return True if the user is a Course Creator (global or by org)."""
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

    def has_permission(self, request, _view) -> bool:  # noqa: D401
        """Return True if the user is staff for the course."""
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        course_key = _get_course_key_from_request(request)
        if course_key is None:
            # No hay forma de validar staff de curso sin contexto del curso
            return False

        return CourseStaffRole(course_key).has_user(user)


class IsAdminOrCourseCreator(BasePermission):
    """Allow access to site admins or course creators."""

    message = "User must be admin or Course Creator"

    def has_permission(self, request, _view) -> bool:
        """Allow if site admin or Course Creator."""
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        # Bypass para administradores del sitio Open edX
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        return IsCourseCreator().has_permission(request, _view)


class IsAdminUser(BasePermission):
    """Allow access only to site admins."""

    message = "User must be an admin"

    def has_permission(self, request, _view) -> bool:
        """Allow if the user is a site admin."""
        user = request.user
        return bool(
            getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))
        )


class IsAdminOrCourseStaff(BasePermission):
    """Allow access to site admins or course staff for the resolved course."""

    message = "User must be admin or Course Staff"

    def has_permission(self, request, _view) -> bool:
        """Allow if site admin or Course Staff for the specified course."""
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        # Bypass para administradores del sitio Open edX
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        return IsCourseStaff().has_permission(request, _view)


class IsAdminOrCourseCreatorOrCourseStaff(BasePermission):
    """Allow access to site admins, course creators, or course staff."""

    message = "User must be admin, Course Creator or Course Staff"

    def has_permission(self, request, _view) -> bool:
        """Allow if admin or has Course Creator/Staff role for the context."""
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        # Bypass para administradores del sitio Open edX
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        # OR entre creador de curso y staff del curso
        return (
            IsCourseCreator().has_permission(request, _view)
            or IsCourseStaff().has_permission(request, _view)
        )
