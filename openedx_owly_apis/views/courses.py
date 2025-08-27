"""
OpenedX Course Management ViewSet
ViewSet simple que mapea directamente las funciones de lógica existentes
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication
from openedx_owly_apis.permissions import (
    IsAdminOrCourseCreator,
    IsAdminOrCourseStaff,
    IsAdminOrCourseCreatorOrCourseStaff,
)

# Importar funciones lógicas originales
from openedx_owly_apis.operations.courses import (
    update_course_settings_logic,
    create_course_logic,
    update_advanced_settings_logic,
    enable_configure_certificates_logic,
    control_unit_availability_logic,
    add_html_content_logic,
    add_video_content_logic,
    add_problem_content_logic,
    add_discussion_content_logic,
    create_course_structure_logic,
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
        Añadir problemas/ejercicios a un vertical
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
        """Configure certificates for a course"""
        data = request.data
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
