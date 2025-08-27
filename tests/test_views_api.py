from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate


@pytest.fixture()
def api_factory():
    return APIRequestFactory()


def _auth_user(**attrs):
    base = dict(
        id=1,
        username="tester",
        is_authenticated=True,
        is_active=True,
        is_superuser=False,
        is_staff=False,
        is_course_staff=False,
        is_course_creator=False,
    )
    base.update(attrs)
    return SimpleNamespace(**base)


class TestOpenedXCourseViewSet:
    def test_create_course_calls_logic_and_returns_payload(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_course"})
        req = api_factory.post(
            "/owly-courses/create/",
            {
                "org": "ORG",
                "course_number": "NUM",
                "run": "RUN",
                "display_name": "Name",
                "start_date": "2024-01-01",
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        body = resp.data
        assert body["called"] == "create_course_logic"
        # kwargs echo back from stubbed logic
        assert body["kwargs"]["org"] == "ORG"

    def test_update_settings_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "update_settings"})
        req = api_factory.post(
            "/owly-courses/settings/update/",
            {"course_id": "course-v1:ORG+NUM+RUN", "settings_data": {"start": "2024-01-01"}},
            format="json",
        )
        req.user = _auth_user()
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "update_course_settings_logic"


class TestOpenedXAnalyticsViewSet:
    def test_overview_calls_logic(self, api_factory):
        from openedx_owly_apis.views.analytics import OpenedXAnalyticsViewSet
        view = OpenedXAnalyticsViewSet.as_view({"get": "analytics_overview"})
        req = api_factory.get("/owly-analytics/overview/", {"course_id": "course-v1:ORG+NUM+RUN"})
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "get_overview_analytics_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:ORG+NUM+RUN"

    def test_enrollments_calls_logic(self, api_factory):
        from openedx_owly_apis.views.analytics import OpenedXAnalyticsViewSet
        view = OpenedXAnalyticsViewSet.as_view({"get": "analytics_enrollments"})
        req = api_factory.get("/owly-analytics/enrollments/", {"course_id": "course-v1:ORG+NUM+RUN"})
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "get_enrollments_analytics_logic"


class TestOpenedXRolesViewSet:
    def test_me_effective_role_resolution(self, api_factory):
        from openedx_owly_apis.views.roles import OpenedXRolesViewSet
        view = OpenedXRolesViewSet.as_view({"get": "me"})
        # Course staff takes precedence over creator and authenticated
        user = _auth_user(is_course_staff=True, is_course_creator=True, is_staff=False, is_superuser=False)
        req = api_factory.get("/owly-roles/me/?course_id=course-v1:ORG+NUM+RUN&org=ORG")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        data = resp.data
        assert data["roles"]["course_staff"] is True
        assert data["roles"]["course_creator"] is True
        assert data["roles"]["authenticated"] is True
        assert data["effective_role"] in {"CourseStaff", "SuperAdmin"}  # SuperAdmin if staff flags set

        # SuperAdmin when is_staff True
        user2 = _auth_user(is_staff=True)
        req2 = api_factory.get("/owly-roles/me/")
        force_authenticate(req2, user=user2)
        resp2 = view(req2)
        assert resp2.status_code == 200
        assert resp2.data["effective_role"] == "SuperAdmin"
