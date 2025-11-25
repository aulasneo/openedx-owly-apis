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
            # Validate basic format for testing purposes
            if s and isinstance(s, str) and s != "invalid-format":
                return cls(s)
            # Raise exception for invalid formats
            raise ValueError(f"Invalid course key: {s}")

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
            return {"success": True, "called": name, "kwargs": kwargs}
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
    ops_courses.manage_course_staff_logic = _simple_ret("manage_course_staff_logic")
    ops_courses.list_course_staff_logic = _simple_ret("list_course_staff_logic")
    ops_courses.toggle_certificate_simple_logic = _simple_ret("toggle_certificate_simple_logic")
    ops_courses.add_ora_content_logic = _simple_ret("add_ora_content_logic")
    ops_courses.grade_ora_content_logic = _simple_ret("grade_ora_content_logic")
    ops_courses.get_ora_details_logic = _simple_ret("get_ora_details_logic")
    ops_courses.list_ora_submissions_logic = _simple_ret("list_ora_submissions_logic")
    ops_courses.create_cohort_logic = _simple_ret("create_cohort_logic")
    ops_courses.list_cohorts_logic = _simple_ret("list_cohorts_logic")
    ops_courses.add_user_to_cohort_logic = _simple_ret("add_user_to_cohort_logic")
    ops_courses.remove_user_from_cohort_logic = _simple_ret("remove_user_from_cohort_logic")
    ops_courses.list_cohort_members_logic = _simple_ret("list_cohort_members_logic")
    ops_courses.delete_cohort_logic = _simple_ret("delete_cohort_logic")
    ops_courses.get_course_tree_logic = _simple_ret("get_course_tree_logic")
    ops_courses.get_vertical_contents_logic = _simple_ret("get_vertical_contents_logic")
    ops_courses.send_bulk_email_logic = _simple_ret("send_bulk_email_logic")
    # Content Groups v2 API stubs with proper parameter handling
    def list_content_groups_logic(course_id, user_identifier=None):
        return {"success": True, "called": "list_content_groups_logic", "course_id": course_id, "user_identifier": user_identifier}
    
    def create_content_group_logic(course_id, name, description=None, user_identifier=None):
        return {"success": True, "called": "create_content_group_logic", "course_id": course_id, "name": name, "description": description, "user_identifier": user_identifier}
    
    def update_content_group_logic(group_id, course_id, name=None, description=None, user_identifier=None):
        return {"success": True, "called": "update_content_group_logic", "group_id": group_id, "course_id": course_id, "name": name, "description": description, "user_identifier": user_identifier}
    
    def delete_content_group_logic(group_id, course_id, user_identifier=None):
        return {"success": True, "called": "delete_content_group_logic", "group_id": group_id, "course_id": course_id, "user_identifier": user_identifier}
    
    def list_content_group_cohort_assignments_logic(course_id, user_identifier=None):
        return {"success": True, "called": "list_content_group_cohort_assignments_logic", "course_id": course_id, "user_identifier": user_identifier}
    
    def assign_content_group_to_cohort_logic(course_id, content_group_id, cohort_id, user_identifier=None):
        return {"success": True, "called": "assign_content_group_to_cohort_logic", "course_id": course_id, "content_group_id": content_group_id, "cohort_id": cohort_id, "user_identifier": user_identifier}
    
    def unassign_content_group_from_cohort_logic(course_id, content_group_id, cohort_id, user_identifier=None):
        return {"success": True, "called": "unassign_content_group_from_cohort_logic", "course_id": course_id, "content_group_id": content_group_id, "cohort_id": cohort_id, "user_identifier": user_identifier}
    
    ops_courses.list_content_groups_logic = list_content_groups_logic
    ops_courses.create_content_group_logic = create_content_group_logic
    ops_courses.update_content_group_logic = update_content_group_logic
    ops_courses.delete_content_group_logic = delete_content_group_logic
    ops_courses.list_content_group_cohort_assignments_logic = list_content_group_cohort_assignments_logic
    ops_courses.assign_content_group_to_cohort_logic = assign_content_group_to_cohort_logic
    ops_courses.unassign_content_group_from_cohort_logic = unassign_content_group_from_cohort_logic
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
            return {"success": True, "called": name, "kwargs": _normalize_args(args, kwargs)}
        return _fn
    ops_analytics.get_overview_analytics_logic = _mk_analytics("get_overview_analytics_logic")
    ops_analytics.get_enrollments_analytics_logic = _mk_analytics("get_enrollments_analytics_logic")
    ops_analytics.get_discussions_analytics_logic = _mk_analytics("get_discussions_analytics_logic")
    ops_analytics.get_detailed_analytics_logic = _mk_analytics("get_detailed_analytics_logic")
    sys.modules["openedx_owly_apis.operations.analytics"] = ops_analytics
    stubs.append("openedx_owly_apis.operations.analytics")

    # Stub configuration operations module
    ops_config = types.ModuleType("openedx_owly_apis.operations.config")

    def _cfg_logic(request, user_email=None):  # pylint: disable=unused-argument
        # Echo a simple payload to assert the view is wiring correctly
        return {"success": True, "called": "is_owly_chat_enabled_logic", "kwargs": {"user_email": user_email}}

    ops_config.is_owly_chat_enabled_logic = _cfg_logic
    sys.modules["openedx_owly_apis.operations.config"] = ops_config
    stubs.append("openedx_owly_apis.operations.config")

    # Add send_bulk_email_logic stub to the courses operations module
    def _mk_courses_stub(name):
        def _fn(*args, **kwargs):
            return {"success": True, "called": name, "kwargs": kwargs}
        return _fn

    # Ensure the courses operations module exists and add the bulk email stub
    if "openedx_owly_apis.operations.courses" not in sys.modules:
        ops_courses = types.ModuleType("openedx_owly_apis.operations.courses")
        sys.modules["openedx_owly_apis.operations.courses"] = ops_courses
    else:
        ops_courses = sys.modules["openedx_owly_apis.operations.courses"]

    # Add all the course operation stubs
    ops_courses.send_bulk_email_logic = _mk_courses_stub("send_bulk_email_logic")
    ops_courses.create_course_logic = _mk_courses_stub("create_course_logic")
    ops_courses.update_course_settings_logic = _mk_courses_stub("update_course_settings_logic")
    ops_courses.create_course_structure_logic = _mk_courses_stub("create_course_structure_logic")
    ops_courses.add_html_content_logic = _mk_courses_stub("add_html_content_logic")
    ops_courses.add_video_content_logic = _mk_courses_stub("add_video_content_logic")
    ops_courses.add_problem_content_logic = _mk_courses_stub("add_problem_content_logic")
    ops_courses.add_discussion_content_logic = _mk_courses_stub("add_discussion_content_logic")
    ops_courses.enable_configure_certificates_logic = _mk_courses_stub("enable_configure_certificates_logic")
    ops_courses.toggle_certificate_simple_logic = _mk_courses_stub("toggle_certificate_simple_logic")
    ops_courses.control_unit_availability_logic = _mk_courses_stub("control_unit_availability_logic")
    ops_courses.update_advanced_settings_logic = _mk_courses_stub("update_advanced_settings_logic")
    ops_courses.manage_course_staff_logic = _mk_courses_stub("manage_course_staff_logic")
    ops_courses.list_course_staff_logic = _mk_courses_stub("list_course_staff_logic")
    ops_courses.add_ora_content_logic = _mk_courses_stub("add_ora_content_logic")
    ops_courses.grade_ora_content_logic = _mk_courses_stub("grade_ora_content_logic")
    ops_courses.get_ora_details_logic = _mk_courses_stub("get_ora_details_logic")
    ops_courses.list_ora_submissions_logic = _mk_courses_stub("list_ora_submissions_logic")
    ops_courses.create_cohort_logic = _mk_courses_stub("create_cohort_logic")
    ops_courses.list_cohorts_logic = _mk_courses_stub("list_cohorts_logic")
    ops_courses.add_user_to_cohort_logic = _mk_courses_stub("add_user_to_cohort_logic")
    ops_courses.remove_user_from_cohort_logic = _mk_courses_stub("remove_user_from_cohort_logic")
    ops_courses.list_cohort_members_logic = _mk_courses_stub("list_cohort_members_logic")
    ops_courses.delete_cohort_logic = _mk_courses_stub("delete_cohort_logic")
    ops_courses.create_openedx_problem_logic = _mk_courses_stub("create_openedx_problem_logic")
    ops_courses.publish_content_logic = _mk_courses_stub("publish_content_logic")
    ops_courses.delete_xblock_logic = _mk_courses_stub("delete_xblock_logic")

    try:
        yield
    finally:
        # Optionally cleanup stubs if needed
        for _ in stubs:
            # Keep stubs for duration of test session; do not delete to avoid re-import churn
            pass
