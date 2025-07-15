import json
import asyncio
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# Importar funciones lógicas de analytics
from openedx_owly_apis.operations.courses import (
    get_overview_analytics_logic,
    get_enrollments_analytics_logic,
    get_discussions_analytics_logic,
    get_detailed_analytics_logic
)


class OpenedXAnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet para analíticas de cursos OpenedX
    """

    @action(detail=False, methods=['get'], url_path='overview')
    def analytics_overview(self, request):
        """
        Get overview analytics for a specific course or platform-wide statistics
        """
        course_id = request.query_params.get('course_id')
        result = asyncio.run(get_overview_analytics_logic(course_id))
        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['get'], url_path='enrollments')
    def analytics_enrollments(self, request):
        """
        Get detailed enrollment analytics for a specific course
        """
        course_id = request.query_params.get('course_id')
        result = asyncio.run(get_enrollments_analytics_logic(course_id))
        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['get'], url_path='discussions')
    def analytics_discussions(self, request):
        """
        Get discussion forum analytics and configuration for a specific course
        """
        course_id = request.query_params.get('course_id')
        result = asyncio.run(get_discussions_analytics_logic(course_id))
        result_data = json.loads(result)
        return Response(result_data)

    @action(detail=False, methods=['get'], url_path='detailed')
    def analytics_detailed(self, request):
        """
        Get comprehensive detailed analytics combining all course data
        """
        course_id = request.query_params.get('course_id')
        result = asyncio.run(get_detailed_analytics_logic(course_id))
        result_data = json.loads(result)
        return Response(result_data)
