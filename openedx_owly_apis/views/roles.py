"""
OpenedX Roles ViewSet
Endpoint para consultar el rol efectivo del usuario autenticado.

Determina:
- SuperAdmin: Django superuser o global staff (user.is_superuser o user.is_staff)
- Course Staff (NO staff de Django): staff/instructor/limited_staff en un curso específico
- CourseCreator: según CourseCreatorRole u OrgContentCreatorRole (respeta settings de edx)
- Authenticated: usuario autenticado básico

Uso:
GET /owly-roles/me?course_id=course-v1:ORG+NUM+RUN&org=ORG
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication

from typing import Optional

from opaque_keys.edx.keys import CourseKey
from common.djangoapps.student.roles import (
    CourseStaffRole,
    CourseInstructorRole,
    CourseLimitedStaffRole,
)
from common.djangoapps.student.auth import user_has_role, CourseCreatorRole, OrgContentCreatorRole


class OpenedXRolesViewSet(viewsets.ViewSet):
    """
    ViewSet para roles del usuario en Open edX.
    """
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated]

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
        Devuelve el rol efectivo del usuario autenticado.
        Query params opcionales:
          - course_id: para evaluar si es staff del curso
          - org: para evaluar course creator a nivel organización
        """
        user = request.user
        course_id = request.query_params.get("course_id")
        org = request.query_params.get("org")

        course_key, course_err = self._parse_course_key(course_id)
        if course_err:
            return Response({"error": course_err}, status=400)

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

        return Response({
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
