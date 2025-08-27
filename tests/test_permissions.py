"""
Unit tests for `openedx_owly_apis.permissions.IsAdminOrCourseCreator`.

This test stubs the minimal Open edX modules required by the permissions
module before importing it, so we can test the real logic without the full
platform installed. We do this inline (pre-import) instead of relying on the
session-wide autouse stubs, to keep this test self-contained.
"""

import sys
import types
from types import SimpleNamespace

import pytest


def _ensure_module(path: str):
    parts = path.split(".")
    base = ""
    for name in parts:
        base = f"{base}.{name}" if base else name
        if base not in sys.modules:
            sys.modules[base] = types.ModuleType(base)
    return sys.modules[path]


# Minimal stubs needed by openedx_owly_apis.permissions
mod = _ensure_module("opaque_keys.edx.keys")


class _CourseKey:
    def __init__(self, raw):
        self._raw = raw
        self.org = None
        if raw and ":" in raw:
            try:
                self.org = raw.split(":", 1)[1].split("+")[0]
            except Exception:  # pylint: disable=broad-exception-caught
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


# Import real permissions module after stubbing dependencies
from openedx_owly_apis.permissions import IsAdminOrCourseCreator  # noqa: E402  pylint: disable=wrong-import-position


class _Req(SimpleNamespace):
    """Lightweight request stub with .user, .query_params, .data."""

    def __init__(self, user=None, query=None, data=None):
        super().__init__(
            user=user or SimpleNamespace(is_authenticated=False),
            query_params=query or {},
            data=data or {},
        )


@pytest.mark.parametrize(
    "user,expected",
    [
        # Not authenticated -> False
        (SimpleNamespace(is_authenticated=False), False),
        # Superuser bypass -> True
        (SimpleNamespace(is_authenticated=True, is_superuser=True, is_staff=False), True),
        # Staff bypass -> True
        (SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=True), True),
    ],
)
def test_is_admin_or_course_creator_admin_bypass(user, expected):
    perm = IsAdminOrCourseCreator()
    req = _Req(user=user)
    assert perm.has_permission(req, None) is expected


def test_is_admin_or_course_creator_global_course_creator_allows():
    # user_has_role stub in tests/conftest.py returns is_course_creator
    user = SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=False, is_course_creator=True)
    perm = IsAdminOrCourseCreator()
    req = _Req(user=user)
    assert perm.has_permission(req, None) is True


def test_is_admin_or_course_creator_org_course_creator_allows():
    # Org-specific course creator: provide org in query; user_has_role sees is_course_creator flag
    user = SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=False, is_course_creator=True)
    perm = IsAdminOrCourseCreator()
    req = _Req(user=user, query={"org": "ORG"})
    assert perm.has_permission(req, None) is True


def test_is_admin_or_course_creator_denies_when_no_roles():
    user = SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=False, is_course_creator=False)
    perm = IsAdminOrCourseCreator()
    req = _Req(user=user)
    assert perm.has_permission(req, None) is False
