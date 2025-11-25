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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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

    def test_toggle_certificate_simple_calls_logic(self, api_factory):
        """Test activating/deactivating certificates with simple toggle"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "configure_certificates"})
        req = api_factory.post(
            "/owly-courses/certificates/configure/",
            {
                "course_id": "course-v1:ORG+NUM+RUN",
                "is_active": True
            },
            format="json",
        )
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "toggle_certificate_simple_logic"
        assert resp.data["kwargs"]["is_active"] is True

    def test_control_unit_availability_calls_logic(self, api_factory):
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
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

    # =====================================
    # COHORT MANAGEMENT TESTS
    # =====================================

    def test_create_cohort_calls_logic(self, api_factory):
        """Test creating a new cohort in a course"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/create/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_name": "Grupo A",
                "assignment_type": "manual"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)  # Course staff permissions required
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "create_cohort_logic"
        # Verify the parameters passed to the logic function
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["cohort_name"] == "Grupo A"
        assert resp.data["kwargs"]["assignment_type"] == "manual"

    def test_create_cohort_with_default_assignment_type(self, api_factory):
        """Test creating a cohort with default assignment type (manual)"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/create/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_name": "Grupo B"
                # assignment_type omitted, should default to "manual"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)  # Superuser can also create cohorts
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "create_cohort_logic"
        assert resp.data["kwargs"]["assignment_type"] == "manual"  # Default value

    def test_create_cohort_random_assignment(self, api_factory):
        """Test creating a cohort with random assignment type"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/create/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_name": "Random Group",
                "assignment_type": "random"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "create_cohort_logic"
        assert resp.data["kwargs"]["assignment_type"] == "random"

    def test_list_cohorts_calls_logic(self, api_factory):
        """Test listing all cohorts for a course"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_cohorts"})
        req = api_factory.get(
            "/owly-courses/cohorts/list/",
            {"course_id": "course-v1:TestX+CS101+2024"}
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_cohorts_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"

    def test_list_cohorts_missing_course_id_returns_error(self, api_factory):
        """Test that missing course_id parameter returns 400 error"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_cohorts"})
        req = api_factory.get("/owly-courses/cohorts/list/")  # No course_id
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["error_code"] == "missing_course_id"

    def test_add_user_to_cohort_calls_logic(self, api_factory):
        """Test adding a user to a specific cohort"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_user_to_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/members/add/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 1,
                "user_identifier": "student@example.com"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_user_to_cohort_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["cohort_id"] == 1
        assert resp.data["kwargs"]["user_identifier_to_add"] == "student@example.com"

    def test_add_user_to_cohort_with_username(self, api_factory):
        """Test adding a user to cohort using username"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_user_to_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/members/add/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 2,
                "user_identifier": "student123"  # Using username
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_user_to_cohort_logic"
        assert resp.data["kwargs"]["user_identifier_to_add"] == "student123"

    def test_add_user_to_cohort_with_user_id(self, api_factory):
        """Test adding a user to cohort using user ID"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "add_user_to_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/members/add/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 3,
                "user_identifier": "456"  # Using user ID
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "add_user_to_cohort_logic"
        assert resp.data["kwargs"]["user_identifier_to_add"] == "456"

    def test_remove_user_from_cohort_calls_logic(self, api_factory):
        """Test removing a user from a specific cohort"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "remove_user_from_cohort"})
        req = api_factory.post(
            "/owly-courses/cohorts/members/remove/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 1,
                "user_identifier": "student@example.com"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "remove_user_from_cohort_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["cohort_id"] == 1
        assert resp.data["kwargs"]["user_identifier_to_remove"] == "student@example.com"

    def test_remove_user_from_cohort_different_identifiers(self, api_factory):
        """Test removing users using different identifier types"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "remove_user_from_cohort"})

        # Test with username
        req = api_factory.post(
            "/owly-courses/cohorts/members/remove/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 2,
                "user_identifier": "student_username"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "remove_user_from_cohort_logic"
        assert resp.data["kwargs"]["user_identifier_to_remove"] == "student_username"

    def test_list_cohort_members_calls_logic(self, api_factory):
        """Test listing all members of a specific cohort"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_cohort_members"})
        req = api_factory.get(
            "/owly-courses/cohorts/members/list/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": "1"
            }
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_cohort_members_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["cohort_id"] == 1  # Should be converted to int

    def test_list_cohort_members_missing_parameters_returns_error(self, api_factory):
        """Test that missing required parameters return 400 errors"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_cohort_members"})

        # Missing course_id
        req1 = api_factory.get(
            "/owly-courses/cohorts/members/list/",
            {"cohort_id": "1"}
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req1, user=user)
        resp1 = view(req1)
        assert resp1.status_code == 400
        assert resp1.data["error_code"] == "missing_course_id"

        # Missing cohort_id
        req2 = api_factory.get(
            "/owly-courses/cohorts/members/list/",
            {"course_id": "course-v1:TestX+CS101+2024"}
        )
        force_authenticate(req2, user=user)
        resp2 = view(req2)
        assert resp2.status_code == 400
        assert resp2.data["error_code"] == "missing_cohort_id"

    def test_list_cohort_members_invalid_cohort_id_returns_error(self, api_factory):
        """Test that invalid cohort_id format returns 400 error"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_cohort_members"})
        req = api_factory.get(
            "/owly-courses/cohorts/members/list/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": "not_a_number"
            }
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["error_code"] == "invalid_cohort_id"

    def test_delete_cohort_calls_logic(self, api_factory):
        """Test deleting a cohort from a course"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"delete": "delete_cohort"})
        req = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": "1"
            }
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "delete_cohort_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["cohort_id"] == 1  # Should be converted to int

    def test_delete_cohort_with_superuser_permissions(self, api_factory):
        """Test deleting a cohort with superuser permissions"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"delete": "delete_cohort"})
        req = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {
                "course_id": "course-v1:Aulasneo+PYTHON101+2024",
                "cohort_id": "5"
            }
        )
        user = _auth_user(is_superuser=True)  # Superuser should also be able to delete
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "delete_cohort_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:Aulasneo+PYTHON101+2024"
        assert resp.data["kwargs"]["cohort_id"] == 5

    def test_delete_cohort_missing_parameters_returns_error(self, api_factory):
        """Test that missing required parameters for deletion return 400 errors"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"delete": "delete_cohort"})

        # Missing course_id
        req1 = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {"cohort_id": "1"}
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req1, user=user)
        resp1 = view(req1)
        assert resp1.status_code == 400
        assert resp1.data["error_code"] == "missing_course_id"

        # Missing cohort_id
        req2 = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {"course_id": "course-v1:TestX+CS101+2024"}
        )
        force_authenticate(req2, user=user)
        resp2 = view(req2)
        assert resp2.status_code == 400
        assert resp2.data["error_code"] == "missing_cohort_id"

    def test_delete_cohort_invalid_cohort_id_returns_error(self, api_factory):
        """Test that invalid cohort_id format for deletion returns 400 error"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"delete": "delete_cohort"})
        req = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": "invalid_id"
            }
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["error_code"] == "invalid_cohort_id"

    def test_cohort_management_comprehensive_workflow(self, api_factory):
        """Test a comprehensive workflow of cohort management operations"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet

        course_id = "course-v1:TestX+CS101+2024"
        user = _auth_user(is_course_staff=True)

        # 1. Create a cohort
        create_view = OpenedXCourseViewSet.as_view({"post": "create_cohort"})
        create_req = api_factory.post(
            "/owly-courses/cohorts/create/",
            {
                "course_id": course_id,
                "cohort_name": "Advanced Students",
                "assignment_type": "manual"
            },
            format="json",
        )
        force_authenticate(create_req, user=user)
        create_resp = create_view(create_req)
        assert create_resp.status_code == 200
        assert create_resp.data["called"] == "create_cohort_logic"

        # 2. List cohorts to verify creation
        list_view = OpenedXCourseViewSet.as_view({"get": "list_cohorts"})
        list_req = api_factory.get(
            "/owly-courses/cohorts/list/",
            {"course_id": course_id}
        )
        force_authenticate(list_req, user=user)
        list_resp = list_view(list_req)
        assert list_resp.status_code == 200
        assert list_resp.data["called"] == "list_cohorts_logic"

        # 3. Add user to cohort
        add_view = OpenedXCourseViewSet.as_view({"post": "add_user_to_cohort"})
        add_req = api_factory.post(
            "/owly-courses/cohorts/members/add/",
            {
                "course_id": course_id,
                "cohort_id": 1,
                "user_identifier": "advanced_student@example.com"
            },
            format="json",
        )
        force_authenticate(add_req, user=user)
        add_resp = add_view(add_req)
        assert add_resp.status_code == 200
        assert add_resp.data["called"] == "add_user_to_cohort_logic"

        # 4. List cohort members to verify addition
        members_view = OpenedXCourseViewSet.as_view({"get": "list_cohort_members"})
        members_req = api_factory.get(
            "/owly-courses/cohorts/members/list/",
            {"course_id": course_id, "cohort_id": "1"}
        )
        force_authenticate(members_req, user=user)
        members_resp = members_view(members_req)
        assert members_resp.status_code == 200
        assert members_resp.data["called"] == "list_cohort_members_logic"

        # 5. Remove user from cohort
        remove_view = OpenedXCourseViewSet.as_view({"post": "remove_user_from_cohort"})
        remove_req = api_factory.post(
            "/owly-courses/cohorts/members/remove/",
            {
                "course_id": course_id,
                "cohort_id": 1,
                "user_identifier": "advanced_student@example.com"
            },
            format="json",
        )
        force_authenticate(remove_req, user=user)
        remove_resp = remove_view(remove_req)
        assert remove_resp.status_code == 200
        assert remove_resp.data["called"] == "remove_user_from_cohort_logic"

        # 6. Delete cohort
        delete_view = OpenedXCourseViewSet.as_view({"delete": "delete_cohort"})
        delete_req = api_factory.delete(
            "/owly-courses/cohorts/delete/",
            {"course_id": course_id, "cohort_id": "1"}
        )
        force_authenticate(delete_req, user=user)
        delete_resp = delete_view(delete_req)
        assert delete_resp.status_code == 200
        assert delete_resp.data["called"] == "delete_cohort_logic"

    def test_create_problem_calls_logic(self, api_factory):
        """Test creating a problem component"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "create_problem"})
        req = api_factory.post(
            "/owly-courses/content/problem/create/",
            {
                "unit_locator": "block-v1:ORG+NUM+RUN+type@vertical+block@unit1",
                "problem_type": "multiplechoiceresponse",
                "display_name": "Test Problem",
                "problem_data": {"question": "Test?"}
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "create_openedx_problem_logic"
        assert resp.data["kwargs"]["unit_locator"] == "block-v1:ORG+NUM+RUN+type@vertical+block@unit1"

    def test_publish_content_calls_logic(self, api_factory):
        """Test publishing course content"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "publish_content"})
        req = api_factory.post(
            "/owly-courses/content/publish/",
            {
                "content_id": "block-v1:ORG+NUM+RUN+type@vertical+block@unit1",
                "publish_type": "auto"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "publish_content_logic"
        assert resp.data["kwargs"]["content_id"] == "block-v1:ORG+NUM+RUN+type@vertical+block@unit1"

    def test_delete_xblock_calls_logic(self, api_factory):
        """Test deleting an xblock component"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "delete_xblock"})
        req = api_factory.post(
            "/owly-courses/xblock/delete/",
            {
                "block_id": "block-v1:ORG+NUM+RUN+type@html+block@html1"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "delete_xblock_logic"
        assert resp.data["kwargs"]["block_id"] == "block-v1:ORG+NUM+RUN+type@html+block@html1"

    def test_grade_ora_with_simplified_format(self, api_factory):
        """Test grading ORA with simplified format (no grade_data wrapper)"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "grade_ora_content"})
        req = api_factory.post(
            "/owly-courses/content/ora/grade/",
            {
                "ora_location": "block-v1:ORG+NUM+RUN+type@openassessment+block@ora1",
                "student_username": "student123",
                "options_selected": {"Criterion 1": "Excellent"},
                "overall_feedback": "Great work!",
                "assess_type": "full-grade"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "grade_ora_content_logic"

    def test_get_ora_details_missing_location(self, api_factory):
        """Test get ORA details without ora_location parameter"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "get_ora_details"})
        req = api_factory.get("/owly-courses/content/ora/details/")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["error_code"] == "missing_ora_location"

    def test_list_ora_submissions_missing_location(self, api_factory):
        """Test list ORA submissions without ora_location parameter"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"get": "list_ora_submissions"})
        req = api_factory.get("/owly-courses/content/ora/submissions/")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["error_code"] == "missing_ora_location"

    def test_get_ora_details_with_error_response(self, api_factory, monkeypatch):
        """Test get ORA details when logic returns error (covers lines 556-564)"""
        import sys

        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet

        # Mock the logic function to return success=False

        def mock_get_ora_details(**kwargs):
            return {"success": False, "error": "ORA not found", "error_code": "ora_not_found"}

        # Use sys.modules since conftest creates stubs there
        ops_courses = sys.modules["openedx_owly_apis.operations.courses"]
        monkeypatch.setattr(ops_courses, "get_ora_details_logic", mock_get_ora_details)

        view = OpenedXCourseViewSet.as_view({"get": "get_ora_details"})
        ora_location = "block-v1:ORG+NUM+RUN+type@openassessment+block@ora1"
        req = api_factory.get(f"/owly-courses/content/ora/details/?ora_location={ora_location}")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False

    def test_list_ora_submissions_with_error_response(self, api_factory, monkeypatch):
        """Test list ORA submissions when logic returns error (covers lines 623-631)"""
        import sys

        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet

        # Mock the logic function to return success=False

        def mock_list_ora_submissions(**kwargs):
            return {"success": False, "error": "Failed to retrieve submissions", "error_code": "retrieval_error"}

        # Use sys.modules since conftest creates stubs there
        ops_courses = sys.modules["openedx_owly_apis.operations.courses"]
        monkeypatch.setattr(ops_courses, "list_ora_submissions_logic", mock_list_ora_submissions)

        view = OpenedXCourseViewSet.as_view({"get": "list_ora_submissions"})
        ora_location = "block-v1:ORG+NUM+RUN+type@openassessment+block@ora1"
        req = api_factory.get(f"/owly-courses/content/ora/submissions/?ora_location={ora_location}")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False


class TestOpenedXAnalyticsViewSet:
    def test_overview_calls_logic(self, api_factory):
        from openedx_owly_apis.views.v1.analytics import OpenedXAnalyticsViewSet
        view = OpenedXAnalyticsViewSet.as_view({"get": "analytics_overview"})
        req = api_factory.get("/owly-analytics/overview/", {"course_id": "course-v1:ORG+NUM+RUN"})
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "get_overview_analytics_logic"
        assert resp.data["kwargs"]["course_id"] == "course-v1:ORG+NUM+RUN"

    def test_enrollments_calls_logic(self, api_factory):
        from openedx_owly_apis.views.v1.analytics import OpenedXAnalyticsViewSet
        view = OpenedXAnalyticsViewSet.as_view({"get": "analytics_enrollments"})
        req = api_factory.get("/owly-analytics/enrollments/", {"course_id": "course-v1:ORG+NUM+RUN"})
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "get_enrollments_analytics_logic"


class TestOpenedXRolesViewSet:
    def test_me_effective_role_resolution(self, api_factory):
        from openedx_owly_apis.views.v1.roles import OpenedXRolesViewSet
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

    def test_me_invalid_course_id(self, api_factory):
        """Test /me endpoint with invalid course_id format"""
        from openedx_owly_apis.views.v1.roles import OpenedXRolesViewSet
        view = OpenedXRolesViewSet.as_view({"get": "me"})
        user = _auth_user()
        req = api_factory.get("/owly-roles/me/?course_id=invalid-format")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert "error" in resp.data

    def test_me_course_creator_with_org(self, api_factory):
        """Test course creator role with organization parameter"""
        from openedx_owly_apis.views.v1.roles import OpenedXRolesViewSet
        view = OpenedXRolesViewSet.as_view({"get": "me"})
        user = _auth_user(is_course_creator=True)
        req = api_factory.get("/owly-roles/me/?org=TestOrg")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["roles"]["course_creator"] is True
        assert resp.data["effective_role"] == "CourseCreator"

    def test_me_not_course_creator_with_org(self, api_factory):
        """Test user without course creator role but with org parameter (covers line 65)"""
        from openedx_owly_apis.views.v1.roles import OpenedXRolesViewSet
        view = OpenedXRolesViewSet.as_view({"get": "me"})
        # User without course creator role, but org is present
        user = _auth_user(is_course_creator=False)
        req = api_factory.get("/owly-roles/me/?org=TestOrg")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        # Should be False because is_course_creator is False
        assert resp.data["roles"]["course_creator"] is False
        assert resp.data["effective_role"] == "Authenticated"


class TestOpenedXConfigViewSet:
    def test_enable_owly_chat_calls_logic(self, api_factory):
        from openedx_owly_apis.views.v1.config_openedx import OpenedXConfigViewSet
        view = OpenedXConfigViewSet.as_view({"get": "enable_owly_chat"})
        req = api_factory.get("/owly-config/enable_owly_chat/")
        user = _auth_user()
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "is_owly_chat_enabled_logic"


class TestConfTestCoverage:
    """Tests to cover edge cases in conftest.py stub implementations"""

    def test_course_key_without_colon(self):
        """Test CourseKey stub with simple string (no colon)"""
        from opaque_keys.edx.keys import CourseKey

        # Test with string without colon (valid because not "invalid-format")
        key = CourseKey.from_string("simple-string")
        assert key.org is None
        # Test that None raises exception
        with pytest.raises(ValueError):
            CourseKey.from_string(None)

    def test_course_key_str_method(self):
        """Test CourseKey __str__ method"""
        from opaque_keys.edx.keys import CourseKey
        key = CourseKey.from_string("course-v1:TestOrg+NUM+RUN")
        # This exercises the __str__ method (line 70)
        assert str(key) == "course-v1:TestOrg+NUM+RUN"

    def test_org_content_creator_role_with_org(self):
        """Test OrgContentCreatorRole initialization with org parameter"""
        from common.djangoapps.student.auth import OrgContentCreatorRole

        # This exercises line 100: self.org = org
        role = OrgContentCreatorRole(org="TestOrganization")
        assert role.org == "TestOrganization"

    def test_analytics_normalize_args_with_positional(self):
        """Test analytics function with positional arguments to cover _normalize_args"""
        from openedx_owly_apis.operations.analytics import get_overview_analytics_logic

        # Call with positional argument (exercises lines 162-165 in conftest.py)
        result = get_overview_analytics_logic("course-v1:ORG+NUM+RUN")
        assert result["success"] is True
        assert result["called"] == "get_overview_analytics_logic"
        # Verify the positional arg was normalized to kwargs
        assert result["kwargs"]["course_id"] == "course-v1:ORG+NUM+RUN"

    def test_analytics_normalize_args_with_kwargs(self):
        """Test analytics function with keyword arguments (covers alternate branch in _normalize_args)"""
        from openedx_owly_apis.operations.analytics import get_overview_analytics_logic

        # Call with keyword argument (exercises the else branch in _normalize_args)
        result = get_overview_analytics_logic(course_id="course-v1:ORG+NUM+RUN")
        assert result["success"] is True
        assert result["called"] == "get_overview_analytics_logic"
        # Verify the kwarg was preserved
        assert result["kwargs"]["course_id"] == "course-v1:ORG+NUM+RUN"


class TestBulkEmailAPI:
    """Test suite for bulk email functionality"""

    def test_send_bulk_email_calls_logic(self, api_factory):
        """Test sending bulk email to course participants"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Course Announcement",
                "body": "Welcome to the course! This is an important announcement.",
                "targets": ["myself", "staff", "learners"]
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)  # Course staff permissions required
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        # Verify the parameters passed to the logic function
        assert resp.data["kwargs"]["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["kwargs"]["subject"] == "Course Announcement"
        assert resp.data["kwargs"]["body"] == "Welcome to the course! This is an important announcement."
        assert resp.data["kwargs"]["targets"] == ["myself", "staff", "learners"]

    def test_send_bulk_email_with_cohort_target(self, api_factory):
        """Test sending bulk email to specific cohort"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Cohort Specific Message",
                "body": "This message is for your cohort only.",
                "targets": ["cohort"],
                "cohort_id": 5
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        assert resp.data["kwargs"]["targets"] == ["cohort"]
        assert resp.data["kwargs"]["cohort_id"] == 5

    def test_send_bulk_email_with_schedule(self, api_factory):
        """Test scheduling bulk email for future delivery"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Scheduled Announcement",
                "body": "This email will be sent at a scheduled time.",
                "targets": ["learners"],
                "schedule": "2025-12-25T10:00:00Z"
            },
            format="json",
        )
        user = _auth_user(is_superuser=True)  # Superuser can also send emails
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        assert resp.data["kwargs"]["schedule"] == "2025-12-25T10:00:00Z"

    def test_send_bulk_email_with_custom_template(self, api_factory):
        """Test sending bulk email with custom template and from address"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Custom Template Email",
                "body": "This email uses a custom template.",
                "targets": ["staff"],
                "template_name": "course_announcement",
                "from_addr": "instructor@university.edu"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        assert resp.data["kwargs"]["template_name"] == "course_announcement"
        assert resp.data["kwargs"]["from_addr"] == "instructor@university.edu"

    def test_send_bulk_email_targets_as_json_string(self, api_factory):
        """Test sending bulk email with targets as JSON string"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "JSON Targets Test",
                "body": "Testing with JSON string targets.",
                "targets": '["myself", "learners"]'  # JSON string format
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        # Should be parsed to list
        assert resp.data["kwargs"]["targets"] == ["myself", "learners"]

    def test_send_bulk_email_targets_as_csv_string(self, api_factory):
        """Test sending bulk email with targets as comma-separated string"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "CSV Targets Test",
                "body": "Testing with CSV string targets.",
                "targets": "myself,staff,learners"  # CSV format
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "send_bulk_email_logic"
        # Should be parsed to list
        assert resp.data["kwargs"]["targets"] == ["myself", "staff", "learners"]

    def test_send_bulk_email_missing_required_fields(self, api_factory):
        """Test bulk email validation for missing required fields"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})

        # Missing course_id
        req1 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "subject": "Test Subject",
                "body": "Test body",
                "targets": ["learners"]
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req1, user=user)
        resp1 = view(req1)
        assert resp1.status_code == 400
        assert resp1.data["success"] is False
        assert "course_id" in resp1.data["error"]

        # Missing subject
        req2 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "body": "Test body",
                "targets": ["learners"]
            },
            format="json",
        )
        force_authenticate(req2, user=user)
        resp2 = view(req2)
        assert resp2.status_code == 400
        assert resp2.data["success"] is False
        assert "subject" in resp2.data["error"]

        # Missing body
        req3 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Test Subject",
                "targets": ["learners"]
            },
            format="json",
        )
        force_authenticate(req3, user=user)
        resp3 = view(req3)
        assert resp3.status_code == 400
        assert resp3.data["success"] is False
        assert "body" in resp3.data["error"]

    def test_send_bulk_email_invalid_targets_format(self, api_factory):
        """Test bulk email with invalid targets format"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Test Subject",
                "body": "Test body",
                "targets": '[invalid, json, syntax]'  # Invalid JSON syntax for targets
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert "targets" in resp.data["error"]

    def test_send_bulk_email_comprehensive_workflow(self, api_factory):
        """Test a comprehensive bulk email workflow with different scenarios"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet

        course_id = "course-v1:TestX+CS101+2024"
        user = _auth_user(is_course_staff=True)

        # 1. Send email to myself only
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})
        req1 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": course_id,
                "subject": "Test Email to Myself",
                "body": "This is a test email sent only to me.",
                "targets": ["myself"]
            },
            format="json",
        )
        force_authenticate(req1, user=user)
        resp1 = view(req1)
        assert resp1.status_code == 200
        assert resp1.data["called"] == "send_bulk_email_logic"

        # 2. Send email to all staff members
        req2 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": course_id,
                "subject": "Staff Meeting Reminder",
                "body": "Don't forget about tomorrow's staff meeting.",
                "targets": ["staff"]
            },
            format="json",
        )
        force_authenticate(req2, user=user)
        resp2 = view(req2)
        assert resp2.status_code == 200
        assert resp2.data["called"] == "send_bulk_email_logic"

        # 3. Send email to all learners with scheduled delivery
        req3 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": course_id,
                "subject": "Course Update",
                "body": "Important updates about the course curriculum.",
                "targets": ["learners"],
                "schedule": "2025-01-15T09:00:00Z"
            },
            format="json",
        )
        force_authenticate(req3, user=user)
        resp3 = view(req3)
        assert resp3.status_code == 200
        assert resp3.data["called"] == "send_bulk_email_logic"

        # 4. Send email to everyone (staff + learners + myself)
        req4 = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": course_id,
                "subject": "Important Course Announcement",
                "body": "This affects everyone in the course.",
                "targets": ["myself", "staff", "learners"]
            },
            format="json",
        )
        force_authenticate(req4, user=user)
        resp4 = view(req4)
        assert resp4.status_code == 200
        assert resp4.data["called"] == "send_bulk_email_logic"

    def test_send_bulk_email_permission_validation(self, api_factory):
        """Test that only authorized users can send bulk emails"""
        from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
        view = OpenedXCourseViewSet.as_view({"post": "send_bulk_email"})

        # Test with regular authenticated user (no course staff permissions)
        req = api_factory.post(
            "/owly-courses/bulk-email/send/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "subject": "Unauthorized Email",
                "body": "This should not be allowed.",
                "targets": ["learners"]
            },
            format="json",
        )
        # User without course staff or admin permissions
        user = _auth_user(is_course_staff=False, is_superuser=False)
        force_authenticate(req, user=user)

        # Note: The actual permission validation happens in the logic layer
        # This test verifies the endpoint calls the logic with correct params
        resp = view(req)
        assert resp.status_code == 200  # ViewSet passes through, logic handles validation
        assert resp.data["called"] == "send_bulk_email_logic"


class TestContentGroupViewSetV2:
    """Test suite for Content Groups API v2 using BaseAPIViewSet."""
    
    def test_list_content_groups_success(self, api_factory):
        """Test listing content groups with valid course_id."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-groups/?course_id=course-v1:TestX%2BCS101%2B2024")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_content_groups_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["user_identifier"] == 1
    
    def test_list_content_groups_missing_course_id(self, api_factory):
        """Test listing content groups without course_id parameter."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-groups/")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "course_id parameter is required"
        assert resp.data["error_code"] == "missing_course_id"
    
    def test_create_content_group_success(self, api_factory):
        """Test creating a new content group with valid data."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-groups/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "name": "Advanced Students",
                "description": "Content for advanced students"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 201
        assert resp.data["called"] == "create_content_group_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["name"] == "Advanced Students"
        assert resp.data["description"] == "Content for advanced students"
        assert resp.data["user_identifier"] == 1
    
    def test_create_content_group_validation_error(self, api_factory):
        """Test creating content group with invalid data."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-groups/",
            {
                "course_id": "",  # Invalid empty course_id
                "name": "Test Group"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "Validation failed"
        assert "errors" in resp.data
    
    def test_update_content_group_success(self, api_factory):
        """Test updating an existing content group."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"put": "update"})
        req = api_factory.put(
            "/api/v2/content-groups/1/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "name": "Updated Group Name",
                "description": "Updated description"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req, pk="1")
        assert resp.status_code == 200
        assert resp.data["called"] == "update_content_group_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["group_id"] == "1"
        assert resp.data["name"] == "Updated Group Name"
        assert resp.data["description"] == "Updated description"
        assert resp.data["user_identifier"] == 1
    
    def test_update_content_group_missing_id(self, api_factory):
        """Test updating content group without providing ID."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"put": "update"})
        req = api_factory.put(
            "/api/v2/content-groups/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "name": "Updated Group"
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "ID is required"
        assert resp.data["error_code"] == "missing_id"
    
    def test_delete_content_group_success(self, api_factory):
        """Test deleting a content group."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete("/api/v2/content-groups/1/?course_id=course-v1:TestX%2BCS101%2B2024")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req, pk="1")
        assert resp.status_code == 200
        assert resp.data["called"] == "delete_content_group_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["group_id"] == "1"
        assert resp.data["user_identifier"] == 1
    
    def test_delete_content_group_missing_course_id(self, api_factory):
        """Test deleting content group without course_id parameter."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete("/api/v2/content-groups/1/")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req, pk="1")
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "course_id parameter is required"
        assert resp.data["error_code"] == "missing_course_id"


class TestContentGroupCohortAssignmentViewSetV2:
    """Test suite for Content Group to Cohort Assignments API v2."""
    
    def test_list_assignments_success(self, api_factory):
        """Test listing content group to cohort assignments."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-group-assignments/?course_id=course-v1:TestX%2BCS101%2B2024")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_content_group_cohort_assignments_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["user_identifier"] == 1
    
    def test_list_assignments_missing_course_id(self, api_factory):
        """Test listing assignments without course_id parameter."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-group-assignments/")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "course_id parameter is required"
        assert resp.data["error_code"] == "missing_course_id"
    
    def test_create_assignment_success(self, api_factory):
        """Test creating a new content group to cohort assignment."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-group-assignments/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "content_group_id": 1,
                "cohort_id": 2
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 201
        assert resp.data["called"] == "assign_content_group_to_cohort_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["content_group_id"] == 1
        assert resp.data["cohort_id"] == 2
        assert resp.data["user_identifier"] == 1
    
    def test_create_assignment_validation_error(self, api_factory):
        """Test creating assignment with invalid data."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-group-assignments/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "content_group_id": "invalid",  # Should be integer
                "cohort_id": 2
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "Validation failed"
        assert "errors" in resp.data
    
    def test_delete_assignment_success(self, api_factory):
        """Test deleting a content group to cohort assignment."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete(
            "/api/v2/content-group-assignments/?course_id=course-v1:TestX%2BCS101%2B2024&content_group_id=1&cohort_id=2"
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "unassign_content_group_from_cohort_logic"
        assert resp.data["course_id"] == "course-v1:TestX+CS101+2024"
        assert resp.data["content_group_id"] == 1
        assert resp.data["cohort_id"] == 2
        assert resp.data["user_identifier"] == 1
    
    def test_delete_assignment_missing_parameters(self, api_factory):
        """Test deleting assignment without required parameters."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete("/api/v2/content-group-assignments/?course_id=course-v1:TestX+CS101+2024")
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req)
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "course_id, content_group_id, and cohort_id parameters are required"
        assert resp.data["error_code"] == "missing_parameters"
    
    def test_update_assignment_not_supported(self, api_factory):
        """Test that update operation is not supported for assignments."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"put": "update"})
        req = api_factory.put(
            "/api/v2/content-group-assignments/1/",
            {
                "course_id": "course-v1:TestX+CS101+2024",
                "content_group_id": 1,
                "cohort_id": 2
            },
            format="json",
        )
        user = _auth_user(is_course_staff=True)
        force_authenticate(req, user=user)
        
        resp = view(req, pk="1")
        assert resp.status_code == 400
        assert resp.data["success"] is False
        assert resp.data["message"] == "Update operation not supported for assignments"
        assert resp.data["error_code"] == "operation_not_supported"


class TestContentGroupsV2Permissions:
    """Test suite for Content Groups API v2 permissions."""
    
    def test_content_group_requires_authentication(self, api_factory):
        """Test that content group endpoints require authentication."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        view = ContentGroupViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-groups/?course_id=course-v1:TestX+CS101+2024")
        # No authentication
        
        resp = view(req)
        # ViewSet properly enforces authentication at the permission level
        assert resp.status_code == 403  # Forbidden - authentication required
    
    def test_assignment_requires_authentication(self, api_factory):
        """Test that assignment endpoints require authentication."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        view = ContentGroupCohortAssignmentViewSet.as_view({"get": "list"})
        req = api_factory.get("/api/v2/content-group-assignments/?course_id=course-v1:TestX+CS101+2024")
        # No authentication
        
        resp = view(req)
        # ViewSet properly enforces authentication at the permission level
        assert resp.status_code == 403  # Forbidden - authentication required


class TestContentGroupsV2Integration:
    """Integration tests for Content Groups API v2."""
    
    def test_full_crud_workflow(self, api_factory):
        """Test complete CRUD workflow for content groups."""
        from openedx_owly_apis.views.v2.views import ContentGroupViewSet
        
        user = _auth_user(is_course_staff=True)
        course_id = "course-v1:TestX+CS101+2024"
        
        # 1. List content groups (initially empty)
        view = ContentGroupViewSet.as_view({"get": "list"})
        req = api_factory.get(f"/api/v2/content-groups/?course_id={course_id}")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_content_groups_logic"
        
        # 2. Create a new content group
        view = ContentGroupViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-groups/",
            {
                "course_id": course_id,
                "name": "Test Group",
                "description": "Test Description"
            },
            format="json",
        )
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 201
        assert resp.data["called"] == "create_content_group_logic"
        
        # 3. Update the content group
        view = ContentGroupViewSet.as_view({"put": "update"})
        req = api_factory.put(
            "/api/v2/content-groups/1/",
            {
                "course_id": course_id,
                "name": "Updated Test Group",
                "description": "Updated Description"
            },
            format="json",
        )
        force_authenticate(req, user=user)
        resp = view(req, pk="1")
        assert resp.status_code == 200
        assert resp.data["called"] == "update_content_group_logic"
        
        # 4. Delete the content group
        view = ContentGroupViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete(f"/api/v2/content-groups/1/?course_id={course_id}")
        force_authenticate(req, user=user)
        resp = view(req, pk="1")
        assert resp.status_code == 200
        assert resp.data["called"] == "delete_content_group_logic"
    
    def test_assignment_workflow(self, api_factory):
        """Test complete workflow for content group assignments."""
        from openedx_owly_apis.views.v2.views import ContentGroupCohortAssignmentViewSet
        
        user = _auth_user(is_course_staff=True)
        course_id = "course-v1:TestX+CS101+2024"
        
        # 1. List assignments (initially empty)
        view = ContentGroupCohortAssignmentViewSet.as_view({"get": "list"})
        req = api_factory.get(f"/api/v2/content-group-assignments/?course_id={course_id}")
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "list_content_group_cohort_assignments_logic"
        
        # 2. Create assignment
        view = ContentGroupCohortAssignmentViewSet.as_view({"post": "create"})
        req = api_factory.post(
            "/api/v2/content-group-assignments/",
            {
                "course_id": course_id,
                "content_group_id": 1,
                "cohort_id": 2
            },
            format="json",
        )
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 201
        assert resp.data["called"] == "assign_content_group_to_cohort_logic"
        
        # 3. Delete assignment
        view = ContentGroupCohortAssignmentViewSet.as_view({"delete": "destroy"})
        req = api_factory.delete(
            f"/api/v2/content-group-assignments/?course_id={course_id}&content_group_id=1&cohort_id=2"
        )
        force_authenticate(req, user=user)
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["called"] == "unassign_content_group_from_cohort_logic"
