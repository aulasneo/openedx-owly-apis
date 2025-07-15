"""
OpenedX Course Management ViewSet
ViewSet simple que mapea directamente las funciones de lógica existentes
"""
import json
import asyncio
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Importar funciones lógicas originales
from openedx_owly_apis.operations.courses import (
    create_course_logic,
    create_course_structure_logic,
    add_html_content_logic,
    add_video_content_logic,
    add_problem_content_logic,
    add_discussion_content_logic
)

class OpenedXCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de cursos OpenedX - mapeo directo de funciones MCP
    """

    @action(detail=False, methods=['post'], url_path='create')
    def create_course(self, request):
        """
        Crear un nuevo curso OpenedX
        Mapea directamente a create_course_logic()
        """
        data = request.data
        result = asyncio.run(create_course_logic(
            org=data.get('org'),
            course_number=data.get('course_number'),
            run=data.get('run'),
            display_name=data.get('display_name'),
            start_date=data.get('start_date')
        ))

        # Parsear el JSON string que retorna la función
        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['post'], url_path='structure')
    def create_structure(self, request):
        """
        Crear/editar estructura del curso
        Mapea directamente a create_course_structure_logic()
        """
        data = request.data
        result = asyncio.run(create_course_structure_logic(
            course_id=data.get('course_id'),
            units_config=data.get('units_config'),
            edit=data.get('edit', False)
        ))

        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['post'], url_path='content/html')
    def add_html_content(self, request):
        """
        Añadir contenido HTML a un vertical
        Mapea directamente a add_html_content_logic()
        """
        data = request.data
        result = asyncio.run(add_html_content_logic(
            vertical_id=data.get('vertical_id'),
            html_config=data.get('html_config')
        ))

        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['post'], url_path='content/video')
    def add_video_content(self, request):
        """
        Añadir contenido de video a un vertical
        Mapea directamente a add_video_content_logic()
        """
        data = request.data
        result = asyncio.run(add_video_content_logic(
            vertical_id=data.get('vertical_id'),
            video_config=data.get('video_config')
        ))

        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['post'], url_path='content/problem')
    def add_problem_content(self, request):
        """
        Añadir problemas/ejercicios a un vertical
        Mapea directamente a add_problem_content_logic()
        """
        data = request.data
        result = asyncio.run(add_problem_content_logic(
            vertical_id=data.get('vertical_id'),
            problem_config=data.get('problem_config')
        ))

        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['post'], url_path='content/discussion')
    def add_discussion_content(self, request):
        """
        Añadir foros de discusión a un vertical
        Mapea directamente a add_discussion_content_logic()
        """
        data = request.data
        result = asyncio.run(add_discussion_content_logic(
            vertical_id=data.get('vertical_id'),
            discussion_config=data.get('discussion_config')
        ))

        result_data = json.loads(result)
        return Response(result_data)

