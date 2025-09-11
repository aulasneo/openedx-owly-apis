"""
Test stubs and fixtures for isolating Open edX dependencies.

This module provides lightweight stub modules so app code can import without the
full Open edX platform during tests.
"""

import sys
import types

import pytest


def _ensure_module(path: str):
    parts = path.split(".")
    base = ""
    for _, name in enumerate(parts):  # pylint: disable=unused-variable
        base = f"{base}.{name}" if base else name
        if base not in sys.modules:
            sys.modules[base] = types.ModuleType(base)
    return sys.modules[path]


@pytest.fixture(autouse=True)
def stub_openedx_modules():  # pylint: disable=too-many-statements
    """
    Stub external Open edX and DRF auth modules so views can import.

    This avoids installing the full Open edX platform during tests.
    """
    stubs = []

    # edx-rest-framework-extensions auth
    mod = _ensure_module("edx_rest_framework_extensions.auth.jwt.authentication")

    class JwtAuthentication:
        def authenticate(self, request):  # pragma: no cover - not used in these tests
            return None
    mod.JwtAuthentication = JwtAuthentication
    stubs.append("edx_rest_framework_extensions.auth.jwt.authentication")

    # openedx.core Bearer auth
    mod = _ensure_module("openedx.core.lib.api.authentication")

    class BearerAuthentication:
        def authenticate(self, request):  # pragma: no cover - not used in these tests
            return None
    mod.BearerAuthentication = BearerAuthentication
    stubs.append("openedx.core.lib.api.authentication")

    # opaque keys minimal stub
    mod = _ensure_module("opaque_keys.edx.keys")

    class _CourseKey:
        def __init__(self, raw):
            self._raw = raw
            # try parse org like course-v1:ORG+NUM+RUN -> ORG
            self.org = None
            if raw and ":" in raw:
                try:
                    self.org = raw.split(":", 1)[1].split("+")[0]
                except Exception:  # pragma: no cover - best effort  # pylint: disable=broad-exception-caught
                    self.org = None

        @classmethod
        def from_string(cls, s):
            return cls(s)

        def __str__(self):
            return self._raw

    class _UsageKey(_CourseKey):
        pass
    mod.CourseKey = _CourseKey
    mod.UsageKey = _UsageKey
    stubs.append("opaque_keys.edx.keys")

    # common.djangoapps student roles/auth minimal
    mod = _ensure_module("common.djangoapps.student.roles")

    class _Role:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def has_user(self, user):
            return getattr(user, "is_course_staff", False)
    mod.CourseInstructorRole = _Role
    mod.CourseStaffRole = _Role
    mod.CourseLimitedStaffRole = _Role
    stubs.append("common.djangoapps.student.roles")

    mod = _ensure_module("common.djangoapps.student.auth")

    class CourseCreatorRole:  # noqa: D401 - dummy
        pass

    class OrgContentCreatorRole:
        def __init__(self, org=None):
            self.org = org

    def user_has_role(user, _role):
        return getattr(user, "is_course_creator", False)
    mod.CourseCreatorRole = CourseCreatorRole
    mod.OrgContentCreatorRole = OrgContentCreatorRole
    mod.user_has_role = user_has_role
    stubs.append("common.djangoapps.student.auth")

    # Replace openedx_owly_apis.permissions with permissive dummies to avoid importing real module
    perm_mod = types.ModuleType("openedx_owly_apis.permissions")

    class _AllowAll:  # mimics DRF BasePermission
        def has_permission(self, request, _view):
            return True
    perm_mod.IsAdminOrCourseCreator = _AllowAll
    perm_mod.IsAdminOrCourseStaff = _AllowAll
    perm_mod.IsAdminOrCourseCreatorOrCourseStaff = _AllowAll
    sys.modules["openedx_owly_apis.permissions"] = perm_mod
    stubs.append("openedx_owly_apis.permissions")

    # Stub operations modules with simple functions so views import succeeds
    ops_courses = types.ModuleType("openedx_owly_apis.operations.courses")

    def _simple_ret(name):
        def _fn(**kwargs):
            return {"called": name, "kwargs": kwargs}
        return _fn
    ops_courses.update_course_settings_logic = _simple_ret("update_course_settings_logic")
    ops_courses.create_course_logic = _simple_ret("create_course_logic")
    ops_courses.update_advanced_settings_logic = _simple_ret("update_advanced_settings_logic")
    ops_courses.enable_configure_certificates_logic = _simple_ret("enable_configure_certificates_logic")
    ops_courses.control_unit_availability_logic = _simple_ret("control_unit_availability_logic")
    ops_courses.add_html_content_logic = _simple_ret("add_html_content_logic")
    ops_courses.add_video_content_logic = _simple_ret("add_video_content_logic")
    ops_courses.add_problem_content_logic = _simple_ret("add_problem_content_logic")
    ops_courses.add_discussion_content_logic = _simple_ret("add_discussion_content_logic")
    ops_courses.create_course_structure_logic = _simple_ret("create_course_structure_logic")
    # Extras importados por las vistas aunque no se usen en estos tests
    ops_courses.create_openedx_problem_logic = _simple_ret("create_openedx_problem_logic")
    ops_courses.publish_content_logic = _simple_ret("publish_content_logic")
    ops_courses.delete_xblock_logic = _simple_ret("delete_xblock_logic")
    sys.modules["openedx_owly_apis.operations.courses"] = ops_courses
    stubs.append("openedx_owly_apis.operations.courses")

    ops_analytics = types.ModuleType("openedx_owly_apis.operations.analytics")

    def _normalize_args(args, kwargs):
        # Views pass course_id positionally; map it into kwargs for easier assertions
        if args and "course_id" not in kwargs:
            kwargs = dict(kwargs)
            kwargs["course_id"] = args[0]
        return kwargs

    def _mk_analytics(name):
        def _fn(*args, **kwargs):
            return {"called": name, "kwargs": _normalize_args(args, kwargs)}
        return _fn
    ops_analytics.get_overview_analytics_logic = _mk_analytics("get_overview_analytics_logic")
    ops_analytics.get_enrollments_analytics_logic = _mk_analytics("get_enrollments_analytics_logic")
    ops_analytics.get_discussions_analytics_logic = _mk_analytics("get_discussions_analytics_logic")
    ops_analytics.get_detailed_analytics_logic = _mk_analytics("get_detailed_analytics_logic")
    sys.modules["openedx_owly_apis.operations.analytics"] = ops_analytics
    stubs.append("openedx_owly_apis.operations.analytics")

    # Stub configuration operations module
    ops_config = types.ModuleType("openedx_owly_apis.operations.config")

    def _cfg_logic(request):  # pylint: disable=unused-argument
        # Echo a simple payload to assert the view is wiring correctly
        return {"called": "is_owly_chat_enabled_logic", "kwargs": {}}

    ops_config.is_owly_chat_enabled_logic = _cfg_logic
    sys.modules["openedx_owly_apis.operations.config"] = ops_config
    stubs.append("openedx_owly_apis.operations.config")

    try:
        yield
    finally:
        # Optionally cleanup stubs if needed
        for _ in stubs:
            # Keep stubs for duration of test session; do not delete to avoid re-import churn
            pass
