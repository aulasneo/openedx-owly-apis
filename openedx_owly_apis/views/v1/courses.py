"""OpenedX course management v1 APIs with explicit request contracts."""

from django.db import transaction
from django.utils.decorators import method_decorator
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from openedx_owly_apis.course_structure_jobs import (
    create_course_structure_job,
    get_course_structure_job,
    update_course_structure_job,
)
# Importar funciones lógicas originales
from openedx_owly_apis.operations.courses import (
    add_discussion_content_logic,
    add_html_content_logic,
    add_problem_content_logic,
    add_video_content_logic,
    control_unit_availability_logic,
    create_course_logic,
    create_course_structure_logic,
    create_openedx_problem_logic,
    delete_xblock_logic,
    enable_configure_certificates_logic,
    get_course_tree_logic,
    get_vertical_contents_logic,
    publish_content_logic,
    rerun_course_logic,
    send_bulk_email_logic,
    update_advanced_settings_logic,
    update_course_settings_logic,
)
from openedx_owly_apis.permissions import (
    IsAdminOrCourseCreator,
    IsAdminOrCourseCreatorOrCourseStaff,
    IsAdminOrCourseStaff,
    IsAdminUser,
    is_admin_user,
    is_course_creator_user,
    is_course_staff_user,
)
from openedx_owly_apis.publish_jobs import (
    create_publish_content_job,
    get_publish_content_job,
    update_publish_content_job,
)
from openedx_owly_apis.tasks import create_course_structure_task, publish_content_task
from openedx_owly_apis.views.v1.response_utils import (
    error_response,
    logic_result_response,
    serializer_error_response,
    success_response,
)
from openedx_owly_apis.views.v1.serializers import (
    BulkEmailRequestSerializer,
    CohortMemberActionRequestSerializer,
    CohortMembersQuerySerializer,
    ConfigureCertificatesRequestSerializer,
    ControlUnitAvailabilityRequestSerializer,
    CourseIdQuerySerializer,
    CourseStructureRequestSerializer,
    CourseTreeQuerySerializer,
    CreateCohortRequestSerializer,
    CreateCourseRequestSerializer,
    CreateProblemComponentRequestSerializer,
    DeleteCohortQuerySerializer,
    DeleteXBlockRequestSerializer,
    DiscussionContentRequestSerializer,
    HtmlContentRequestSerializer,
    ListCourseStaffQuerySerializer,
    ManageCourseStaffRequestSerializer,
    OraContentRequestSerializer,
    OraGradeRequestSerializer,
    OraLocationQuerySerializer,
    ProblemContentRequestSerializer,
    PublishContentRequestSerializer,
    RerunCourseRequestSerializer,
    UnitContentsQuerySerializer,
    UpdateAdvancedSettingsRequestSerializer,
    UpdateCourseSettingsRequestSerializer,
    VideoContentRequestSerializer,
)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class OpenedXCourseViewSet(viewsets.ViewSet):
    """
    Course management endpoints for Open edX.

    Authentication is required for all actions. Individual endpoints declare the
    minimum additional permission checks needed for the underlying operation.
    """
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _validated(serializer_class, *, data=None, context=None):
        serializer = serializer_class(data=data, context=context or {})
        if not serializer.is_valid():
            return None, serializer_error_response(serializer)
        return serializer.validated_data, None

    @staticmethod
    def _can_access_structure_job(user, job):
        if is_admin_user(user):
            return True

        requested_by = str(job.get("requested_by")) if job.get("requested_by") is not None else None
        if requested_by and requested_by == str(user.id):
            return True

        course_id = job.get("course_id")
        if not course_id:
            return False

        try:
            course_key = CourseKey.from_string(course_id)
        except Exception:  # pylint: disable=broad-except
            return False

        return (
            is_course_staff_user(user, course_key)
            or is_course_creator_user(user, getattr(course_key, "org", None))
        )

    @staticmethod
    def _course_id_from_content_id(content_id):
        if isinstance(content_id, str) and ("+type@" in content_id or content_id.startswith("block-v1:")):
            try:
                usage_key = UsageKey.from_string(content_id)
                course_key = getattr(usage_key, "course_key", None)
                if course_key:
                    return str(course_key)
            except Exception:  # pylint: disable=broad-except
                pass

        try:
            return str(CourseKey.from_string(content_id))
        except Exception:  # pylint: disable=broad-except
            pass

        return None

    def _can_access_publish_job(self, user, job):
        if is_admin_user(user):
            return True

        requested_by = str(job.get("requested_by")) if job.get("requested_by") is not None else None
        if requested_by and requested_by == str(user.id):
            return True

        course_id = job.get("course_id")
        if not course_id:
            course_id = self._course_id_from_content_id(job.get("content_id"))
        if not course_id:
            return False

        try:
            course_key = CourseKey.from_string(course_id)
        except Exception:  # pylint: disable=broad-except
            return False

        return (
            is_course_staff_user(user, course_key)
            or is_course_creator_user(user, getattr(course_key, "org", None))
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='create',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreator],
    )
    def create_course(self, request):
        data, error = self._validated(CreateCourseRequestSerializer, data=request.data)
        if error:
            return error
        result = create_course_logic(
            org=data.get('org'),
            course_number=data.get('course_number'),
            run=data.get('run'),
            display_name=data.get('display_name'),
            start_date=data.get('start_date'),
            user_identifier=request.user.id
        )
        return logic_result_response(result, success_status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['post'],
        url_path='rerun',
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def rerun_course(self, request):
        data, error = self._validated(RerunCourseRequestSerializer, data=request.data)
        if error:
            return error
        result = rerun_course_logic(
            source_course_id=data.get('course_id'),
            run=data.get('run'),
            display_name=data.get('display_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            org=data.get('org'),
            course_number=data.get('course_number'),
            background=data.get('background', True),
            user_identifier=request.user.id,
        )
        return logic_result_response(result, success_status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['post'],
        url_path='structure',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def create_structure(self, request):
        data, error = self._validated(CourseStructureRequestSerializer, data=request.data)
        if error:
            return error
        result = create_course_structure_logic(
            course_id=data.get('course_id'),
            units_config=data.get('units_config'),
            edit=data.get('edit', False),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='structure/async',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def create_structure_async(self, request):
        """Enqueue course structure creation and return a cache-backed job id."""
        data, error = self._validated(CourseStructureRequestSerializer, data=request.data)
        if error:
            return error

        course_id = data["course_id"]
        units_config = data["units_config"]
        edit = data["edit"]

        job = create_course_structure_job(
            course_id=course_id,
            edit=edit,
            user_identifier=request.user.id,
        )

        async_result = create_course_structure_task.delay(
            job["job_id"],
            course_id,
            units_config,
            edit,
            request.user.id,
        )
        update_course_structure_job(job["job_id"], task_id=async_result.id)

        return success_response(
            {
                "job_id": job["job_id"],
                "status": "pending",
                "course_id": course_id,
                "edit_mode": bool(edit),
            },
            http_status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=False,
        methods=['get'],
        url_path=r'structure/jobs/(?P<job_id>[^/.]+)',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def get_structure_job(self, request, job_id=None):
        """Return the current status for an async course structure job."""
        job = get_course_structure_job(job_id)
        if not job:
            return error_response(
                "Async course structure job not found",
                "job_not_found",
                details={"job_id": job_id},
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if not self._can_access_structure_job(request.user, job):
            return error_response(
                "You do not have access to this async course structure job",
                "job_access_denied",
                details={"job_id": job_id},
                http_status=status.HTTP_403_FORBIDDEN,
            )

        return success_response(
            {
                "job_id": job["job_id"],
                "status": job.get("status"),
                "course_id": job.get("course_id"),
                "edit_mode": job.get("edit_mode"),
                "requested_by": job.get("requested_by"),
                "task_id": job.get("task_id"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "progress_message": job.get("progress_message"),
                "result": job.get("result"),
                "error": job.get("error"),
                "completed_at": job.get("completed_at"),
            }
        )

    @action(
        detail=False,
        methods=['get'],
        url_path='tree',
        # permission_classes=[AllowAny],
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def get_course_tree(self, request):
        """
        Get the tree structure of an OpenedX course.

        This endpoint returns the hierarchical structure of a course, allowing you to:
        - Get the complete course tree (course -> chapters -> sequentials -> verticals -> components)
        - Start from a specific block and get its subtree
        - Limit the depth of traversal

        Query parameters:
            course_id (str): Course identifier (e.g., "course-v1:Org+Course+Run")
            starting_block_id (str, optional): Block ID to start from. If not provided, starts from course root.
            depth (int, optional): Maximum depth to traverse. If not provided, returns full tree.
            search_id (str, optional): Exact search by block ID
            search_type (str, optional): Exact search by block type (course, chapter, sequential, vertical, etc.)
            search_name (str, optional): Regex search by display_name (case-insensitive)

        Examples:
            # Get full course tree
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024

            # Get only course with chapters (depth=2)
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&depth=2

            # Get subtree starting from a specific chapter
            GET /api/v1/owly-courses/tree/
            ?course_id=course-v1:TestX+CS101+2024
            &starting_block_id=block-v1:TestX+CS101+2024+type@chapter+block@chapter1

            # Search examples
            # Find all video components
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&search_type=video

            # Find blocks with "quiz" in the name (regex)
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&search_name=.*quiz.*

            # Find specific block by ID
            GET /api/v1/owly-courses/tree/
            ?course_id=course-v1:TestX+CS101+2024
            &search_id=block-v1:TestX+CS101+2024+type@html+block@abc123

        Returns:
            JSON response with course tree structure::

                {
                    "success": true,
                    "course_id": "course-v1:...",
                    "root": "block-v1:...",
                    "structure": {
                        "id": "block-v1:...",
                        "type": "course",
                        "display_name": "Course Name",
                        "children": [
                            {
                                "id": "block-v1:...",
                                "type": "chapter",
                                "display_name": "Chapter 1",
                                "children": [...]
                            }
                        ]
                    },
                    "search_results": [  // Only present when search parameters are used
                        {
                            "id": "block-v1:...",
                            "type": "video",
                            "display_name": "Introduction Video"
                        }
                    ],
                    "search_count": 1  // Only present when search parameters are used
                }
        """
        data, error = self._validated(CourseTreeQuerySerializer, data=request.query_params)
        if error:
            return error

        result = get_course_tree_logic(
            course_id=data.get('course_id'),
            starting_block_id=data.get('starting_block_id'),
            depth=data.get('depth'),
            search_id=data.get('search_id'),
            search_type=data.get('search_type'),
            search_name=data.get('search_name'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='unit/contents',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff]
    )
    def get_unit_contents(self, request):
        """
        List the children of a unit (vertical) and return their raw content where possible.

        Query parameters:
            course_id (str): Course identifier (e.g., "course-v1:Org+Course+Run")
            vertical_id (str): Usage key of the vertical to inspect

        Returns:
            JSON with children entries including id, type, display_name, and content payload per block type.
        """
        data, error = self._validated(UnitContentsQuerySerializer, data=request.query_params)
        if error:
            return error

        result = get_vertical_contents_logic(
            course_id=data.get('course_id'),
            vertical_id=data.get('vertical_id'),
            user_identifier=request.user.id,
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/html',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_html_content(self, request):
        """
        Add an HTML component to a vertical.
        """
        data, error = self._validated(HtmlContentRequestSerializer, data=request.data)
        if error:
            return error
        result = add_html_content_logic(
            vertical_id=data.get('vertical_id'),
            html_config=data.get('html_config'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/video',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_video_content(self, request):
        """
        Add a video component to a vertical.
        """
        data, error = self._validated(VideoContentRequestSerializer, data=request.data)
        if error:
            return error
        result = add_video_content_logic(
            vertical_id=data.get('vertical_id'),
            video_config=data.get('video_config'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/problem',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_problem_content(self, request):
        """
        Add a raw problem component to a vertical.
        """
        data, error = self._validated(ProblemContentRequestSerializer, data=request.data)
        if error:
            return error
        result = add_problem_content_logic(
            vertical_id=data.get('vertical_id'),
            problem_config=data.get('problem_config'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/discussion',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_discussion_content(self, request):
        """
        Add a discussion component to a vertical.
        """
        data, error = self._validated(DiscussionContentRequestSerializer, data=request.data)
        if error:
            return error
        result = add_discussion_content_logic(
            vertical_id=data.get('vertical_id'),
            discussion_config=data.get('discussion_config'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='settings/update',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def update_settings(self, request):
        """
        Update general course settings such as dates and metadata.
        """
        data, error = self._validated(UpdateCourseSettingsRequestSerializer, data=request.data)
        if error:
            return error
        result = update_course_settings_logic(
            course_id=data.get('course_id'),
            settings_data=data.get('settings_data', {}),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='settings/advanced',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def update_advanced_settings(self, request):
        """
        Update advanced course settings stored in ``other_course_settings``.
        """
        data, error = self._validated(UpdateAdvancedSettingsRequestSerializer, data=request.data)
        if error:
            return error
        result = update_advanced_settings_logic(
            course_id=data.get('course_id'),
            advanced_settings=data.get('advanced_settings', {}),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='certificates/configure',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def configure_certificates(self, request):
        """
        Configure certificates for a course.

        Use ``course_id`` and ``is_active`` to toggle certificates on or off.
        Use ``certificate_config`` to update certificate settings.
        """
        data, error = self._validated(ConfigureCertificatesRequestSerializer, data=request.data)
        if error:
            return error
        # Activar/desactivar certificado (solo course_id + is_active)
        if 'is_active' in data:
            # pylint: disable=import-outside-toplevel
            from openedx_owly_apis.operations.courses import toggle_certificate_simple_logic
            result = toggle_certificate_simple_logic(
                course_id=data.get('course_id'),
                is_active=data.get('is_active', True),
                user_identifier=request.user.id
            )
        else:
            # Configuración avanzada
            result = enable_configure_certificates_logic(
                course_id=data.get('course_id'),
                certificate_config=data.get('certificate_config', {}),
                user_identifier=request.user.id
            )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='units/availability/control',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def control_unit_availability(self, request):
        """Update availability and due date settings for a unit."""
        data, error = self._validated(ControlUnitAvailabilityRequestSerializer, data=request.data)
        if error:
            return error
        result = control_unit_availability_logic(
            unit_id=data.get('unit_id'),
            availability_config=data.get('availability_config', {}),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/problem/create',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def create_problem(self, request):
        """Create a structured problem component inside a course unit."""
        data, error = self._validated(CreateProblemComponentRequestSerializer, data=request.data)
        if error:
            return error
        result = create_openedx_problem_logic(
            unit_locator=data.get('unit_locator'),
            problem_type=data.get('problem_type', 'multiplechoiceresponse'),
            display_name=data.get('display_name', 'New Problem'),
            problem_data=data.get('problem_data', {}),
            user_identifier=request.user.id
        )
        return logic_result_response(result, success_status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/publish',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def publish_content(self, request):
        """Publish course content such as courses, sections, subsections, or units."""
        data, error = self._validated(PublishContentRequestSerializer, data=request.data)
        if error:
            return error
        result = publish_content_logic(
            content_id=data.get('content_id'),
            publish_type=data.get('publish_type', 'auto'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/publish/async',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def publish_content_async(self, request):
        """Enqueue content publishing and return a cache-backed job id."""
        data, error = self._validated(PublishContentRequestSerializer, data=request.data)
        if error:
            return error

        content_id = data["content_id"]
        publish_type = data["publish_type"]
        course_id = self._course_id_from_content_id(content_id)

        job = create_publish_content_job(
            content_id=content_id,
            publish_type=publish_type,
            user_identifier=request.user.id,
            course_id=course_id,
        )

        async_result = publish_content_task.delay(
            job["job_id"],
            content_id,
            publish_type,
            request.user.id,
        )
        update_publish_content_job(job["job_id"], task_id=async_result.id)

        return success_response(
            {
                "job_id": job["job_id"],
                "status": "pending",
                "content_id": content_id,
                "publish_type": publish_type,
                "course_id": course_id,
            },
            http_status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=False,
        methods=['get'],
        url_path=r'content/publish/jobs/(?P<job_id>[^/.]+)',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def get_publish_content_job(self, request, job_id=None):
        """Return the current status for an async content publish job."""
        job = get_publish_content_job(job_id)
        if not job:
            return error_response(
                "Async publish job not found",
                "job_not_found",
                details={"job_id": job_id},
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if not self._can_access_publish_job(request.user, job):
            return error_response(
                "You do not have access to this async publish job",
                "job_access_denied",
                details={"job_id": job_id},
                http_status=status.HTTP_403_FORBIDDEN,
            )

        return success_response(
            {
                "job_id": job["job_id"],
                "status": job.get("status"),
                "content_id": job.get("content_id"),
                "publish_type": job.get("publish_type"),
                "course_id": job.get("course_id"),
                "requested_by": job.get("requested_by"),
                "task_id": job.get("task_id"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "progress_message": job.get("progress_message"),
                "result": job.get("result"),
                "error": job.get("error"),
                "completed_at": job.get("completed_at"),
            }
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='xblock/delete',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def delete_xblock(self, request):
        """
        Delete an XBlock component from a course.
        """
        data, error = self._validated(DeleteXBlockRequestSerializer, data=request.data)
        if error:
            return error
        result = delete_xblock_logic(
            block_id=data.get('block_id'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='staff/manage',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def manage_course_staff(self, request):
        """
        Add or remove users from course staff roles.

        Supports the following role types:
            staff: Course staff role (can edit course content)
            course_creator: Global course creator role (can create new courses)

        Body parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            user_identifier (str): User to add/remove (username, email, or user_id)
            action (str): "add" or "remove"
            role_type (str): "staff" or "course_creator"

        Returns:
            Response: JSON response with operation result
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import manage_course_staff_logic
        data, error = self._validated(ManageCourseStaffRequestSerializer, data=request.data)
        if error:
            return error
        result = manage_course_staff_logic(
            course_id=data.get('course_id'),
            user_identifier=data.get('user_identifier'),
            action=data.get('action'),
            role_type=data.get('role_type', 'staff'),
            acting_user_identifier=request.user.username
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='staff/list',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def list_course_staff(self, request):
        """
        List users with course staff roles.

        Query parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            role_type (str, optional): Filter by role type - "staff", "course_creator", or omit for all

        Examples:
            GET /api/v1/owly-courses/staff/list/?course_id=course-v1:TestX+CS101+2024
            GET /api/v1/owly-courses/staff/list/?course_id=course-v1:TestX+CS101+2024&role_type=staff
            GET /api/v1/owly-courses/staff/list/?course_id=course-v1:TestX+CS101+2024&role_type=course_creator

        Returns:
            Response: JSON response with list of users and their roles
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import list_course_staff_logic

        data, error = self._validated(ListCourseStaffQuerySerializer, data=request.query_params)
        if error:
            return error

        result = list_course_staff_logic(
            course_id=data.get('course_id'),
            role_type=data.get('role_type'),
            acting_user_identifier=request.user.username
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/ora',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_ora_content(self, request):
        """
        Add an Open Response Assessment (ORA) component to a vertical.

        ORA components support peer, self, and staff assessment workflows.

        Body parameters:
            vertical_id (str): Identifier of the target vertical
            ora_config (dict): ORA configuration containing:

                * display_name (str): ORA title
                * prompt (str): Prompt shown to learners
                * rubric (dict): Rubric definition
                * assessments (list): Assessment types such as self, peer, or staff
                * submission_start (str, optional): Submission start time (ISO datetime)
                * submission_due (str, optional): Submission due time (ISO datetime)
                * allow_text_response (bool, optional): Whether text submissions are allowed
                * allow_file_upload (bool, optional): Whether file uploads are allowed
                * file_upload_type (str, optional): Allowed upload type, for example ``image`` or ``pdf-and-image``
                * leaderboard_show (int, optional): Number of top submissions to show

        Returns:
            JSON response with the operation result.
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import add_ora_content_logic

        data, error = self._validated(OraContentRequestSerializer, data=request.data)
        if error:
            return error
        result = add_ora_content_logic(
            vertical_id=data.get('vertical_id'),
            ora_config=data.get('ora_config'),
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/ora/grade',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def grade_ora_content(self, request):
        """
        Grade an ORA (Open Response Assessment) submission using staff assessment.

        This endpoint allows staff members to grade student submissions for ORA components
        using OpenedX's internal staff grading functionality.

        Body parameters:
            ora_location (str): ORA XBlock usage key/location
            student_username (str): Username of the student to grade (alternative to submission_uuid)
            submission_uuid (str): UUID of the submission to grade (alternative to student_username)
            options_selected (dict): Selected rubric options for each criterion
            overall_feedback (str): Optional overall feedback for the submission
            criterion_feedback (dict): Optional feedback for each criterion
            assess_type (str): 'full-grade' or 'regrade' (default: 'full-grade')

        Note:
            Either student_username OR submission_uuid must be provided, not both.

        Example request body (simplified format)::

            {
                "ora_location": "block-v1:Org+Course+Run+type@openassessment+block@ora_id",
                "student_username": "student123",
                "options_selected": {
                    "Criterion 1": "Excellent",
                    "Criterion 2": "Good"
                },
                "overall_feedback": "Overall excellent submission"
            }

        Legacy format (still supported)::

            {
                "ora_location": "block-v1:Org+Course+Run+type@openassessment+block@ora_id",
                "submission_uuid": "submission-uuid-here",
                "grade_data": {
                    "options_selected": {
                        "Criterion 1": "Excellent",
                        "Criterion 2": "Good"
                    },
                    "overall_feedback": "Overall excellent submission"
                }
            }

        Returns:
            JSON response with grading result including:

            - success: Boolean indicating operation success
            - message: Success message
            - assessment_id: ID of the created assessment
            - submission_uuid: UUID of the graded submission
            - ora_location: Location of the ORA component
            - student_response: Student's submitted response including:
                - submission_uuid: UUID of the submission
                - submitted_at: Timestamp of submission
                - student_id: Student item ID
                - answer: Student's answer containing:
                    - text: Text response(s) from the student
                    - files: List of uploaded files (if any) with file_key, file_name, file_description
            - grade_data: The grading data that was applied
            - points_earned: Points earned by the student
            - points_possible: Maximum possible points
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import grade_ora_content_logic

        data, error = self._validated(OraGradeRequestSerializer, data=request.data)
        if error:
            return error

        # Support both old format (grade_data) and new simplified format
        grade_data = data.get('grade_data', {})
        if not grade_data:
            # New simplified format
            grade_data = {
                'options_selected': data.get('options_selected', {}),
                'criterion_feedback': data.get('criterion_feedback', {}),
                'overall_feedback': data.get('overall_feedback', ''),
                'assess_type': data.get('assess_type', 'full-grade')
            }

        result = grade_ora_content_logic(
            ora_location=data.get('ora_location'),
            student_username=data.get('student_username'),
            submission_uuid=data.get('submission_uuid'),
            grade_data=grade_data,
            user_identifier=request.user.id
        )
        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='content/ora/details',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def get_ora_details(self, request):
        """
        Get detailed information about an ORA component including rubric structure.

        This endpoint provides comprehensive information about an ORA component,
        including the rubric criteria, options, and expected format for grading.

        Query Parameters:
            ora_location (str): ORA XBlock usage key/location identifier

                Format: "block-v1:ORG+COURSE+RUN+type@openassessment+block@ORA_ID"

                Example: "block-v1:TestX+CS101+2024+type@openassessment+block@essay_ora"

        Returns:
            JSON response containing:

            - success: Boolean indicating operation success
            - ora_info: Detailed ORA component information including:

                - ora_location: The ORA component location
                - display_name: Component title
                - prompt: ORA instructions for students
                - submission_start/due: Deadline information
                - assessment_steps: Available assessment types
                - rubric: Complete rubric structure with criteria and options

            - example_options_selected: Example format for grade_ora_content
            - criterion_names: List of criterion names for easy reference

        Usage Examples:
            GET /api/v1/owly-courses/content/ora/details/?ora_location=block-v1:...

            Use the returned criterion_names and option names for grading::

                POST /api/v1/owly-courses/content/ora/grade/
                {
                    "ora_location": "block-v1:...",
                    "submission_uuid": "12345678-1234-5678-9abc-123456789abc",
                    "grade_data": {
                        "options_selected": {
                            "criterion_name_from_response": "option_name_from_response"
                        }
                    }
                }

        Error Scenarios:
            - INVALID_ORA_LOCATION: Malformed ORA location identifier
            - ORA_NOT_FOUND: ORA component doesn't exist
            - NOT_ORA_XBLOCK: Component exists but isn't an ORA
            - PERMISSION_DENIED: User lacks access to view ORA details
        """
        data, error = self._validated(OraLocationQuerySerializer, data=request.query_params)
        if error:
            return error
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import get_ora_details_logic

        result = get_ora_details_logic(
            ora_location=data.get('ora_location'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='content/ora/submissions',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def list_ora_submissions(self, request):
        """
        List all submissions for a specific ORA component to help identify which students have submitted responses.

        This endpoint helps staff identify which students have submitted responses to an ORA,
        making it easier to know who can be graded.

        Query parameters:
            ora_location (str): ORA XBlock usage key/location

        Example request::

            GET /api/v1/owly-courses/content/ora/submissions/
            ?ora_location=block-v1:Org+Course+Run+type@openassessment+block@ora_id

        Example response::

            {
                "success": true,
                "ora_location": "block-v1:Org+Course+Run+type@openassessment+block@ora_id",
                "total_submissions": 2,
                "submissions": [
                    {
                        "submission_uuid": "f0973a23-0e98-4642-b183-df29acf6339a",
                        "student_id": "1",
                        "student_username": "student1",
                        "student_email": "student1@example.com",
                        "submitted_at": "2025-10-06T20:30:00Z",
                        "created_at": "2025-10-06T20:29:00Z",
                        "attempt_number": 1,
                        "status": "completed"
                    }
                ],
                "message": "Found 2 submissions for this ORA"
            }

        Error Scenarios:
            - INVALID_ORA_LOCATION: Malformed ORA location identifier
            - SUBMISSIONS_RETRIEVAL_ERROR: Failed to retrieve submissions
            - PERMISSION_DENIED: User lacks access to view submissions
        """
        data, error = self._validated(OraLocationQuerySerializer, data=request.query_params)
        if error:
            return error

        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import list_ora_submissions_logic

        result = list_ora_submissions_logic(
            ora_location=data.get('ora_location'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    # =====================================
    # COHORT MANAGEMENT ENDPOINTS
    # =====================================

    @action(
        detail=False,
        methods=['post'],
        url_path='cohorts/create',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def create_cohort(self, request):
        """
        Create a new cohort in an OpenedX course.

        This endpoint allows course staff to create cohorts for organizing students
        into smaller groups within a course.

        Body parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            cohort_name (str): Name for the new cohort
            assignment_type (str, optional): Type of assignment - "manual" (default) or "random"

        Example request body::

            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_name": "Group A",
                "assignment_type": "manual"
            }

        Returns:
            JSON response with cohort creation result including cohort ID and details
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import create_cohort_logic

        data, error = self._validated(CreateCohortRequestSerializer, data=request.data)
        if error:
            return error
        result = create_cohort_logic(
            course_id=data.get('course_id'),
            cohort_name=data.get('cohort_name'),
            assignment_type=data.get('assignment_type', 'manual'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='cohorts/list',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def list_cohorts(self, request):
        """
        List all cohorts in a course.

        This endpoint retrieves all cohorts configured for a specific course,
        including their member counts and assignment types.

        Query parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)

        Example request::

            GET /api/v1/owly-courses/cohorts/list/?course_id=course-v1:TestX+CS101+2024

        Returns:
            JSON response with list of cohorts and their details
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import list_cohorts_logic

        data, error = self._validated(CourseIdQuerySerializer, data=request.query_params)
        if error:
            return error

        result = list_cohorts_logic(
            course_id=data.get('course_id'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='cohorts/members/add',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def add_user_to_cohort(self, request):
        """
        Add a user to a specific cohort.

        This endpoint allows course staff to add students to cohorts for
        group-based learning activities and content organization.

        Body parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            cohort_id (int): ID of the cohort to add user to
            user_identifier (str): User to add (username, email, or user_id)

        Example request body::

            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 1,
                "user_identifier": "student@example.com"
            }

        Returns:
            JSON response with operation result and user/cohort details
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import add_user_to_cohort_logic

        data, error = self._validated(CohortMemberActionRequestSerializer, data=request.data)
        if error:
            return error
        result = add_user_to_cohort_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier_to_add=data.get('user_identifier'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='cohorts/members/remove',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def remove_user_from_cohort(self, request):
        """
        Remove a user from a specific cohort.

        This endpoint allows course staff to remove students from cohorts
        when reorganizing groups or handling course membership changes.

        Body parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            cohort_id (int): ID of the cohort to remove user from
            user_identifier (str): User to remove (username, email, or user_id)

        Example request body::

            {
                "course_id": "course-v1:TestX+CS101+2024",
                "cohort_id": 1,
                "user_identifier": "student@example.com"
            }

        Returns:
            JSON response with operation result and user/cohort details
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import remove_user_from_cohort_logic

        data, error = self._validated(CohortMemberActionRequestSerializer, data=request.data)
        if error:
            return error
        result = remove_user_from_cohort_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier_to_remove=data.get('user_identifier'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='cohorts/members/list',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def list_cohort_members(self, request):
        """
        List all members of a specific cohort.

        This endpoint retrieves detailed information about all users
        currently assigned to a particular cohort.

        Query parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            cohort_id (int): ID of the cohort to list members for

        Example request::

            GET /api/v1/owly-courses/cohorts/members/list/?course_id=course-v1:TestX+CS101+2024&cohort_id=1

        Returns:
            JSON response with list of cohort members and their details
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import list_cohort_members_logic

        merged_data = {
            "course_id": request.query_params.get('course_id') or request.data.get('course_id'),
            "cohort_id": request.query_params.get('cohort_id') or request.data.get('cohort_id'),
        }
        data, error = self._validated(CohortMembersQuerySerializer, data=merged_data)
        if error:
            return error

        result = list_cohort_members_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['delete'],
        url_path='cohorts/delete',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def delete_cohort(self, request):
        """
        Delete a cohort from a course.

        This endpoint allows course staff to permanently remove a cohort
        and all its membership associations from a course.

        Query parameters:
            course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
            cohort_id (int): ID of the cohort to delete

        Example request::

            DELETE /api/v1/owly-courses/cohorts/delete/?course_id=course-v1:TestX+CS101+2024&cohort_id=1

        Warning:
            This operation is irreversible. All user assignments to this cohort will be lost.

        Returns:
            JSON response with deletion result and summary of affected data
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import delete_cohort_logic

        merged_data = {
            "course_id": request.query_params.get('course_id') or request.data.get('course_id'),
            "cohort_id": request.query_params.get('cohort_id') or request.data.get('cohort_id'),
        }
        data, error = self._validated(DeleteCohortQuerySerializer, data=merged_data)
        if error:
            return error

        result = delete_cohort_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier=request.user.id
        )

        return logic_result_response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='bulk/send_email',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def send_bulk_email(self, request):
        """Send bulk email in a course using Open edX internal APIs.

        Body parameters:
            - subject (str): Email subject (required)
            - message (str): HTML body (required)
            - targets (list[str] | str): Optional. Examples: ["myself", "staff", "learners",
              "cohort:MyCohort", "track:verified"]. If a string is provided and looks like
              a JSON array, it will be parsed.
            - cohort_id (int): Optional. If provided and targets is not set, will target that cohort.
            - schedule (str): Optional ISO-8601 datetime (UTC) for scheduling.
            - template_name (str): Optional CourseEmailTemplate name.
            - from_addr (str): Optional custom email "from" address.
            - course_id (str): Course identifier (e.g., "course-v1:Org+Course+Run"). Required.
        """
        data, error = self._validated(BulkEmailRequestSerializer, data=request.data)
        if error:
            return error

        result = send_bulk_email_logic(
            course_id=data.get('course_id'),
            subject=data.get('subject'),
            body=data.get('body'),
            targets=data.get('targets'),
            cohort_id=data.get('cohort_id'),
            schedule=data.get('schedule'),
            template_name=data.get('template_name'),
            from_addr=data.get('from_addr'),
            user_identifier=request.user.id,
        )
        return logic_result_response(result)
