from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

# pylint: disable=import-outside-toplevel, redefined-outer-name


@pytest.fixture()
def api_factory():
    return APIRequestFactory()


def _auth_user(**attrs):
    base = {
        "id": 1,
        "username": "tester",
        "is_authenticated": True,
        "is_active": True,
        "is_superuser": False,
        "is_staff": False,
        "is_course_staff": False,
        "is_course_creator": False,
    }
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
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "update_course_settings_logic"

    def test_create_structure_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_structure"})
        req = api_factory.post(
            "/owly-courses/structure/",
            {"course_id": "course-v1:ORG+NUM+RUN", "units_config": {"sections": []}, "edit": True},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "create_course_structure_logic"

    def test_add_html_content_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_html_content"})
        req = api_factory.post(
            "/owly-courses/content/html/",
            {"vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1", "html_config": {"html": "<p>x</p>"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_html_content_logic"

    def test_add_video_content_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_video_content"})
        req = api_factory.post(
            "/owly-courses/content/video/",
            {"vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1", "video_config": {"url": "http://v"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_video_content_logic"

    def test_add_problem_content_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_problem_content"})
        req = api_factory.post(
            "/owly-courses/content/problem/",
            {"vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1", "problem_config": {"xml": "<problem/>"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_problem_content_logic"

    def test_add_discussion_content_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_discussion_content"})
        req = api_factory.post(
            "/owly-courses/content/discussion/",
            {"vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1", "discussion_config": {"topic": "t"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_discussion_content_logic"

    def test_configure_certificates_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "configure_certificates"})
        req = api_factory.post(
            "/owly-courses/certificates/configure/",
            {"course_id": "course-v1:ORG+NUM+RUN", "certificate_config": {"enabled": True}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "enable_configure_certificates_logic"

    @pytest.mark.skip(reason="toggle_certificate_logic requires full OpenedX environment")
    def test_toggle_certificate_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "configure_certificates"})
        req = api_factory.post(
            "/owly-courses/certificates/configure/",
            {
                "course_id": "course-v1:ORG+NUM+RUN",
                "certificate_id": "cert123",
                "is_active": True
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "toggle_certificate_logic"

    def test_control_unit_availability_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "control_unit_availability"})
        req = api_factory.post(
            "/owly-courses/units/availability/control/",
            {"unit_id": "block-v1:ORG+NUM+RUN+type@sequential+block@u1", "availability_config": {"due": "2024-01-31"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "control_unit_availability_logic"

    def test_update_advanced_settings_calls_logic(self, api_factory):
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "update_advanced_settings"})
        req = api_factory.post(
            "/owly-courses/settings/advanced/",
            {"course_id": "course-v1:ORG+NUM+RUN", "advanced_settings": {"key": "value"}},
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "update_advanced_settings_logic"

    def test_manage_course_staff_add_staff_calls_logic(self, api_factory):
        """Test adding a user to course staff role"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "manage_course_staff"})
        req = api_factory.post(
            "/owly-courses/staff/manage/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "user_identifier": "john.doe@example.com",
                "action": "add",
                "role_type": "staff"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)  # User needs course staff permissions
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "manage_course_staff_logic"
        # Verify the parameters passed to the logic function
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["user_identifier"] == "john.doe@example.com"
        assert resp.data["kwargs"]["action"] == "add"
        assert resp.data["kwargs"]["role_type"] == "staff"

    def test_manage_course_staff_remove_staff_calls_logic(self, api_factory):
        """Test removing a user from course staff role"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "manage_course_staff"})
        req = api_factory.post(
            "/owly-courses/staff/manage/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "user_identifier": "john.doe",
                "action": "remove",
                "role_type": "staff"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)  # Superuser can manage staff
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "manage_course_staff_logic"
        assert resp.data["kwargs"]["action"] == "remove"
        assert resp.data["kwargs"]["role_type"] == "staff"

    def test_manage_course_staff_add_course_creator_calls_logic(self, api_factory):
        """Test adding a user to course creator role (OWLY-178 use case)"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "manage_course_staff"})
        req = api_factory.post(
            "/owly-courses/staff/manage/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "user_identifier": "creator@example.com",
                "action": "add",
                "role_type": "course_creator"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)  # Only superuser can manage course creators
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "manage_course_staff_logic"
        assert resp.data["kwargs"]["role_type"] == "course_creator"
        assert resp.data["kwargs"]["action"] == "add"

    def test_manage_course_staff_remove_course_creator_calls_logic(self, api_factory):
        """Test removing a user from course creator role (OWLY-178 specific case)"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "manage_course_staff"})
        req = api_factory.post(
            "/owly-courses/staff/manage/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "user_identifier": "creator@example.com",
                "action": "remove",
                "role_type": "course_creator"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "manage_course_staff_logic"
        assert resp.data["kwargs"]["role_type"] == "course_creator"
        assert resp.data["kwargs"]["action"] == "remove"

    def test_manage_course_staff_with_user_id_calls_logic(self, api_factory):
        """Test managing staff using user_id instead of email/username"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "manage_course_staff"})
        req = api_factory.post(
            "/owly-courses/staff/manage/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "user_identifier": "123",  # Using user_id
                "action": "add",
                "role_type": "staff"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "manage_course_staff_logic"
        assert resp.data["kwargs"]["user_identifier"] == "123"

    def test_list_course_staff_all_roles_calls_logic(self, api_factory):
        """Test listing all users with course staff roles"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_course_staff"})
        req = api_factory.get(
            "/owly-courses/staff/list/",
            {"course_id": "course-v1:TestX+CS101+2024"}
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_course_staff_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["role_type"] is None  # No filter

    def test_list_course_staff_filter_by_staff_calls_logic(self, api_factory):
        """Test listing only course staff users"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_course_staff"})
        req = api_factory.get(
            "/owly-courses/staff/list/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "role_type": "staff"
            }
        )
        user = _auth_user(is_superuser=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_course_staff_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["role_type"] == "staff"

    def test_list_course_staff_filter_by_course_creator_calls_logic(self, api_factory):
        """Test listing only course creator users"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_course_staff"})
        req = api_factory.get(
            "/owly-courses/staff/list/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "role_type": "course_creator"
            }
        )
        user = _auth_user(is_superuser=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_course_staff_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["role_type"] == "course_creator"

    def test_list_course_staff_different_course_calls_logic(self, api_factory):
        """Test listing staff for different course"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_course_staff"})
        req = api_factory.get(
            "/owly-courses/staff/list/",
            {"course_id": "course-v1:Aulasneo+PYTHON101+2024"}
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_course_staff_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:Aulasneo+PYTHON101+2024"
        assert resp.data["kwargs"]["acting_user_identifier"] == "tester"

    def test_add_ora_content_calls_logic(self, api_factory):
        """Test ORA (Open Response Assessment) content creation endpoint"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_ora_content"})

        # Test data with complete ORA configuration
        ora_config = {
            "display_name": "Test Essay Assignment",
            "prompt": "Write a 500-word essay analyzing the topic.",
            "rubric": {
                "criteria": [
                    {
                        "name": "Content Quality",
                        "prompt": "How well does the essay address the topic?",
                        "options": [
                            {"name": "Excellent", "points": 4, "explanation": "Thoroughly addresses topic"},
                            {"name": "Good", "points": 3, "explanation": "Addresses topic well"},
                            {"name": "Fair", "points": 2, "explanation": "Partially addresses topic"},
                            {"name": "Poor", "points": 1, "explanation": "Does not address topic"}
                        ]
                    },
                    {
                        "name": "Organization",
                        "prompt": "How well organized is the essay?",
                        "options": [
                            {"name": "Very Clear", "points": 4, "explanation": "Excellent structure"},
                            {"name": "Clear", "points": 3, "explanation": "Good structure"},
                            {"name": "Somewhat Clear", "points": 2, "explanation": "Basic structure"},
                            {"name": "Unclear", "points": 1, "explanation": "Poor structure"}
                        ]
                    }
                ]
            },
            "assessments": [
                {"name": "peer", "must_grade": 2, "must_be_graded_by": 2},
                {"name": "self", "must_grade": 1, "must_be_graded_by": 1}
            ],
            "submission_due": "2025-12-31T23:59:59Z",
            "allow_text_response": True,
            "allow_file_upload": False
        }

        req = api_factory.post(
            "/owly-courses/content/ora/",
            {
                "vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1",
                "ora_config": ora_config
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_ora_content_logic"

        # Verify the correct parameters were passed to the logic function
        assert resp.data["kwargs"]["vertical_id"] == "block-v1:ORG+NUM+RUN+type@vertical+block@v1"
        assert resp.data["kwargs"]["ora_config"]["display_name"] == "Test Essay Assignment"
        assert len(resp.data["kwargs"]["ora_config"]["assessments"]) == 2
        assert resp.data["kwargs"]["ora_config"]["rubric"]["criteria"][0]["name"] == "Content Quality"

    def test_add_ora_content_minimal_config(self, api_factory):
        """Test ORA creation with minimal configuration (self-assessment only)"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_ora_content"})

        # Minimal ORA configuration
        minimal_ora_config = {
            "display_name": "Simple Reflection",
            "prompt": "Write a brief reflection on what you learned.",
            "assessments": [
                {"name": "self", "must_grade": 1, "must_be_graded_by": 1}
            ],
            "allow_text_response": True
        }

        req = api_factory.post(
            "/owly-courses/content/ora/",
            {
                "vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1",
                "ora_config": minimal_ora_config
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_ora_content_logic"

        # Verify minimal config is handled correctly
        assert resp.data["kwargs"]["ora_config"]["display_name"] == "Simple Reflection"
        assert len(resp.data["kwargs"]["ora_config"]["assessments"]) == 1
        assert resp.data["kwargs"]["ora_config"]["assessments"][0]["name"] == "self"

    def test_add_ora_content_with_file_upload(self, api_factory):
        """Test adding ORA content with file upload configuration"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_ora_content"})
        req = api_factory.post(
            "/owly-courses/content/ora/",
            {
                "vertical_id": "block-v1:TestX+CS101+2024+type@vertical+block@unit1",
                "ora_config": {
                    "display_name": "Project Upload ORA",
                    "prompt": "Upload your final project",
                    "allow_text_response": True,
                    "allow_file_upload": True,
                    "file_upload_type": "pdf-and-image",
                    "assessments": [
                        {"name": "peer", "must_grade": 1, "must_be_graded_by": 2}
                    ]
                }
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_ora_content_logic"

    def test_grade_ora_content_calls_logic(self, api_factory):
        """Test grading an ORA submission"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "grade_ora_content"})
        req = api_factory.post(
            "/owly-courses/content/ora/grade/",
            {
                "ora_location": "block-v1:TestX+CS101+2024+type@openassessment+block@essay_ora",
                "submission_uuid": "12345678-1234-5678-9abc-123456789abc",
                "grade_data": {
                    "options_selected": {
                        "Content Quality": "Excellent",
                        "Writing Clarity": "Good",
                        "Critical Thinking": "Excellent"
                    },
                    "criterion_feedback": {
                        "Content Quality": "Demonstrates deep understanding",
                        "Writing Clarity": "Generally clear but some areas need improvement"
                    },
                    "overall_feedback": "Strong analytical essay with excellent content",
                    "assess_type": "full-grade"
                }
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)  # Staff permissions required for grading
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "grade_ora_content_logic"
        # Verify the parameters passed to the logic function
        assert resp.data["kwargs"]["ora_location"] == "block-v1:TestX+CS101+2024+type@openassessment+block@essay_ora"
        assert resp.data["kwargs"]["submission_uuid"] == "12345678-1234-5678-9abc-123456789abc"
        assert "grade_data" in resp.data["kwargs"]
        assert resp.data["kwargs"]["grade_data"]["assess_type"] == "full-grade"

    def test_grade_ora_content_minimal_data(self, api_factory):
        """Test grading ORA with minimal required data"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "grade_ora_content"})
        req = api_factory.post(
            "/owly-courses/content/ora/grade/",
            {
                "ora_location": "block-v1:TestX+CS101+2024+type@openassessment+block@simple_ora",
                "submission_uuid": "87654321-4321-8765-dcba-987654321abc",
                "grade_data": {
                    "options_selected": {
                        "Overall Quality": "Good"
                    }
                }
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "grade_ora_content_logic"

    def test_grade_ora_content_regrade(self, api_factory):
        """Test regrading an ORA submission"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "grade_ora_content"})
        req = api_factory.post(
            "/owly-courses/content/ora/grade/",
            {
                "ora_location": "block-v1:TestX+CS101+2024+type@openassessment+block@essay_ora",
                "submission_uuid": "regrade-uuid-1234-5678-9abc-123456789abc",
                "grade_data": {
                    "options_selected": {
                        "Content Quality": "Excellent",
                        "Writing Clarity": "Excellent"
                    },
                    "overall_feedback": "Improved significantly after revision",
                    "assess_type": "regrade"
                }
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "grade_ora_content_logic"
        assert resp.data["kwargs"]["grade_data"]["assess_type"] == "regrade"
        """Test ORA creation with file upload capabilities"""
        from openedx_owly_apis.views.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_ora_content"})

        # ORA configuration with file upload
        file_upload_ora_config = {
            "display_name": "Project Submission",
            "prompt": "Upload your final project and provide a brief description.",
            "assessments": [
                {"name": "peer", "must_grade": 1, "must_be_graded_by": 1}
            ],
            "allow_text_response": True,
            "allow_file_upload": True,
            "file_upload_type": "pdf-and-image"
        }

        req = api_factory.post(
            "/owly-courses/content/ora/",
            {
                "vertical_id": "block-v1:ORG+NUM+RUN+type@vertical+block@v1",
                "ora_config": file_upload_ora_config
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_ora_content_logic"

        # Verify file upload configuration
        assert resp.data["kwargs"]["ora_config"]["allow_file_upload"] is True
        assert resp.data["kwargs"]["ora_config"]["file_upload_type"] == "pdf-and-image"


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


class TestOpenedXConfigViewSet:
    def test_enable_owly_chat_calls_logic(self, api_factory):
        from openedx_owly_apis.views.config_openedx import OpenedXConfigViewSet
        view = OpenedXConfigViewSet.as_view({"get": "enable_owly_chat"})
        req = api_factory.get("/owly-config/enable_owly_chat/")
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "is_owly_chat_enabled_logic"
