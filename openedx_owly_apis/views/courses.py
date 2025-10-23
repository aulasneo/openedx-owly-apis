"""
OpenedX Course Management ViewSet
ViewSet simple que mapea directamente las funciones de lógica existentes
"""
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

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
    publish_content_logic,
    update_advanced_settings_logic,
    update_course_settings_logic,
)
from openedx_owly_apis.permissions import (
    IsAdminOrCourseCreator,
    IsAdminOrCourseCreatorOrCourseStaff,
    IsAdminOrCourseStaff,
)


class OpenedXCourseViewSet(viewsets.ViewSet):
    """
    ViewSet para gestión de cursos OpenedX - mapeo directo de funciones MCP
    Requiere autenticación y permisos de administrador
    """
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='create',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreator],
    )
    def create_course(self, request):
        """
        Crear un nuevo curso OpenedX
        Mapea directamente a create_course_logic()
        """
        data = request.data
        result = create_course_logic(
            org=data.get('org'),
            course_number=data.get('course_number'),
            run=data.get('run'),
            display_name=data.get('display_name'),
            start_date=data.get('start_date'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='structure',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def create_structure(self, request):
        """
        Crear/editar estructura del curso
        Mapea directamente a create_course_structure_logic()
        """
        data = request.data
        result = create_course_structure_logic(
            course_id=data.get('course_id'),
            units_config=data.get('units_config'),
            edit=data.get('edit', False),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['get'],
        url_path='tree',
        permission_classes=[IsAdminOrCourseCreator],
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
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&starting_block_id=block-v1:TestX+CS101+2024+type@chapter+block@chapter1

            # Search examples
            # Find all video components
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&search_type=video

            # Find blocks with "quiz" in the name (regex)
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&search_name=.*quiz.*

            # Find specific block by ID
            GET /api/v1/owly-courses/tree/?course_id=course-v1:TestX+CS101+2024&search_id=block-v1:TestX+CS101+2024+type@html+block@abc123

        Returns:
            JSON response with course tree structure:
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
        course_id = request.query_params.get('course_id')
        starting_block_id = request.query_params.get('starting_block_id')
        depth = request.query_params.get('depth')
        search_id = request.query_params.get('search_id')
        search_type = request.query_params.get('search_type')
        search_name = request.query_params.get('search_name')

        if not course_id:
            return Response({
                'success': False,
                'error': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }, status=400)

        # Convert depth to int if provided
        if depth:
            try:
                depth = int(depth)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'depth must be a valid integer',
                    'error_code': 'invalid_depth'
                }, status=400)

        result = get_course_tree_logic(
            course_id=course_id,
            starting_block_id=starting_block_id,
            depth=depth,
            search_id=search_id,
            search_type=search_type,
            search_name=search_name,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/html',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_html_content(self, request):
        """
        Añadir contenido HTML a un vertical
        Mapea directamente a add_html_content_logic()
        """
        data = request.data
        result = add_html_content_logic(
            vertical_id=data.get('vertical_id'),
            html_config=data.get('html_config'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/video',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_video_content(self, request):
        """
        Añadir contenido de video a un vertical
        Mapea directamente a add_video_content_logic()
        """
        data = request.data
        result = add_video_content_logic(
            vertical_id=data.get('vertical_id'),
            video_config=data.get('video_config'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/problem',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_problem_content(self, request):
        """
        Añadir problema (XML/edx) a un vertical
        Mapea directamente a add_problem_content_logic()
        """
        data = request.data
        result = add_problem_content_logic(
            vertical_id=data.get('vertical_id'),
            problem_config=data.get('problem_config'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/discussion',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_discussion_content(self, request):
        """
        Añadir foros de discusión a un vertical
        Mapea directamente a add_discussion_content_logic()
        """
        data = request.data
        result = add_discussion_content_logic(
            vertical_id=data.get('vertical_id'),
            discussion_config=data.get('discussion_config'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='settings/update',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def update_settings(self, request):
        """
        Actualizar configuraciones del curso (fechas, detalles, etc.)
        Mapea directamente a update_course_settings_logic()
        """
        data = request.data
        result = update_course_settings_logic(
            course_id=data.get('course_id'),
            settings_data=data.get('settings_data', {}),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='settings/advanced',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def update_advanced_settings(self, request):
        """
        Actualizar configuraciones avanzadas del curso (other_course_settings)
        Mapea directamente a update_advanced_settings_logic()
        """
        data = request.data
        result = update_advanced_settings_logic(
            course_id=data.get('course_id'),
            advanced_settings=data.get('advanced_settings', {}),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='certificates/configure',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def configure_certificates(self, request):
        """
        Configure certificates for a course.
        For activation/deactivation, ONLY course_id and is_active are required (no certificate_id).
        For configuration, use certificate_config.
        """
        data = request.data
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
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='units/availability/control',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def control_unit_availability(self, request):
        """Control unit availability and due dates"""
        data = request.data
        result = control_unit_availability_logic(
            unit_id=data.get('unit_id'),
            availability_config=data.get('availability_config', {}),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/problem/create',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def create_problem(self, request):
        """Create a problem component in an OpenEdX course unit"""
        data = request.data
        result = create_openedx_problem_logic(
            unit_locator=data.get('unit_locator'),
            problem_type=data.get('problem_type', 'multiplechoiceresponse'),
            display_name=data.get('display_name', 'New Problem'),
            problem_data=data.get('problem_data', {}),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/publish',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def publish_content(self, request):
        """Publish course content (courses, units, subsections, sections)"""
        data = request.data
        result = publish_content_logic(
            content_id=data.get('content_id'),
            publish_type=data.get('publish_type', 'auto'),
            user_identifier=request.user.id
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='xblock/delete',
        permission_classes=[IsAuthenticated, IsAdminOrCourseStaff],
    )
    def delete_xblock(self, request):
        """
        Delete an xblock component from a course
        Mapped to delete_xblock_logic()
        """
        data = request.data
        result = delete_xblock_logic(
            block_id=data.get('block_id'),
            user_identifier=request.user.id
        )
        return Response(result)

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
        data = request.data
        result = manage_course_staff_logic(
            course_id=data.get('course_id'),
            user_identifier=data.get('user_identifier'),
            action=data.get('action'),
            role_type=data.get('role_type', 'staff'),
            acting_user_identifier=request.user.username
        )
        return Response(result)

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

        course_id = request.query_params.get('course_id')
        role_type = request.query_params.get('role_type')

        result = list_course_staff_logic(
            course_id=course_id,
            role_type=role_type,
            acting_user_identifier=request.user.username
        )
        return Response(result)

    @action(
        detail=False,
        methods=['post'],
        url_path='content/ora',
        permission_classes=[IsAuthenticated, IsAdminOrCourseCreatorOrCourseStaff],
    )
    def add_ora_content(self, request):
        """
        Añadir Open Response Assessment (ORA) a un vertical.

        ORAs permiten evaluaciones por pares, autoevaluaciones y evaluaciones por staff.
        Mapea directamente a add_ora_content_logic()

        Body parameters:
            vertical_id (str): ID del vertical donde agregar el ORA
            ora_config (dict): Configuración del ORA con:

                * display_name (str): Nombre del ORA
                * prompt (str): Pregunta/prompt para los estudiantes
                * rubric (dict): Configuración de la rúbrica de evaluación
                * assessments (list): Tipos de evaluación (self, peer, staff)
                * submission_start (str, optional): Inicio de entregas (ISO datetime)
                * submission_due (str, optional): Fecha límite entregas (ISO datetime)
                * allow_text_response (bool, optional): Permitir respuestas de texto
                * allow_file_upload (bool, optional): Permitir subida de archivos
                * file_upload_type (str, optional): 'image', 'pdf-and-image', etc.
                * leaderboard_show (int, optional): Número de mejores entregas a mostrar

        Returns:
            Response: JSON response con resultado de la operación
        """
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import add_ora_content_logic

        data = request.data
        result = add_ora_content_logic(
            vertical_id=data.get('vertical_id'),
            ora_config=data.get('ora_config'),
            user_identifier=request.user.id
        )
        return Response(result)

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

        data = request.data

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
        return Response(result)

    @action(detail=False, methods=['get'], url_path='content/ora/details')
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
        ora_location = request.query_params.get('ora_location')

        if not ora_location:
            return Response({
                'success': False,
                'error': 'ora_location parameter is required',
                'error_code': 'missing_ora_location'
            }, status=400)
        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import get_ora_details_logic

        result = get_ora_details_logic(
            ora_location=ora_location,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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
        ora_location = request.query_params.get('ora_location')

        if not ora_location:
            return Response({
                'success': False,
                'error': 'ora_location parameter is required',
                'error_code': 'missing_ora_location'
            }, status=400)

        # pylint: disable=import-outside-toplevel
        from openedx_owly_apis.operations.courses import list_ora_submissions_logic

        result = list_ora_submissions_logic(
            ora_location=ora_location,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        data = request.data
        result = create_cohort_logic(
            course_id=data.get('course_id'),
            cohort_name=data.get('cohort_name'),
            assignment_type=data.get('assignment_type', 'manual'),
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        course_id = request.query_params.get('course_id')

        if not course_id:
            return Response({
                'success': False,
                'error': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }, status=400)

        result = list_cohorts_logic(
            course_id=course_id,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        data = request.data
        result = add_user_to_cohort_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier_to_add=data.get('user_identifier'),
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        data = request.data
        result = remove_user_from_cohort_logic(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            user_identifier_to_remove=data.get('user_identifier'),
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        # Accept parameters from both query_params and data for test compatibility
        course_id = request.query_params.get('course_id') or request.data.get('course_id')
        cohort_id = request.query_params.get('cohort_id') or request.data.get('cohort_id')

        if not course_id:
            return Response({
                'success': False,
                'error': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }, status=400)

        if not cohort_id:
            return Response({
                'success': False,
                'error': 'cohort_id parameter is required',
                'error_code': 'missing_cohort_id'
            }, status=400)

        try:
            cohort_id = int(cohort_id)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'cohort_id must be a valid integer',
                'error_code': 'invalid_cohort_id'
            }, status=400)

        result = list_cohort_members_logic(
            course_id=course_id,
            cohort_id=cohort_id,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)

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

        # Accept parameters from both query_params and data for test compatibility
        course_id = request.query_params.get('course_id') or request.data.get('course_id')
        cohort_id = request.query_params.get('cohort_id') or request.data.get('cohort_id')

        if not course_id:
            return Response({
                'success': False,
                'error': 'course_id parameter is required',
                'error_code': 'missing_course_id'
            }, status=400)

        if not cohort_id:
            return Response({
                'success': False,
                'error': 'cohort_id parameter is required',
                'error_code': 'missing_cohort_id'
            }, status=400)

        try:
            cohort_id = int(cohort_id)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'cohort_id must be a valid integer',
                'error_code': 'invalid_cohort_id'
            }, status=400)

        result = delete_cohort_logic(
            course_id=course_id,
            cohort_id=cohort_id,
            user_identifier=request.user.id
        )

        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)
