"""
OpenedX Course Management ViewSet
ViewSet simple que mapea directamente las funciones de lógica existentes
"""
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
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
            * ora_location (str): ORA XBlock usage key/location
            * student_username (str): Username of the student to grade (alternative to submission_uuid)
            * submission_uuid (str): UUID of the submission to grade (alternative to student_username)
            * options_selected (dict): Selected rubric options for each criterion
            * overall_feedback (str): Optional overall feedback for the submission
            * criterion_feedback (dict): Optional feedback for each criterion
            * assess_type (str): 'full-grade' or 'regrade' (default: 'full-grade')

        Note: Either student_username OR submission_uuid must be provided, not both.

        Example request body (simplified format):
        {
            "ora_location": "block-v1:Org+Course+Run+type@openassessment+block@ora_id",
            "student_username": "student123",
            "options_selected": {
                "Criterion 1": "Excellent",
                "Criterion 2": "Good"
            },
            "overall_feedback": "Overall excellent submission"
        }
        Legacy format (still supported):
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
            Response: JSON response with grading result including assessment ID and success status
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
            - ora_location (str): ORA XBlock usage key/location identifier
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
            
            # Use the returned criterion_names and option names for grading:
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
            * ora_location (str): ORA XBlock usage key/location

        Example request:
        GET /api/v1/owly-courses/content/ora/submissions/?ora_location=block-v1:Org+Course+Run+type@openassessment+block@ora_id

        Example response:
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
        
        from openedx_owly_apis.operations.courses import list_ora_submissions_logic
        
        result = list_ora_submissions_logic(
            ora_location=ora_location,
            user_identifier=request.user.id
        )
        
        status_code = 200 if result.get('success') else 400
        return Response(result, status=status_code)
