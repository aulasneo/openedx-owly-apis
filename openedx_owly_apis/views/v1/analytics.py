from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

# Importar funciones lógicas de analytics
from openedx_owly_apis.operations.analytics import (
    get_detailed_analytics_logic,
    get_discussions_analytics_logic,
    get_enrollments_analytics_logic,
    get_overview_analytics_logic,
)
from openedx_owly_apis.permissions import IsAdminOrCourseStaff
from openedx_owly_apis.views.v1.response_utils import logic_result_response, serializer_error_response
from openedx_owly_apis.views.v1.serializers import (
    CourseScopedAnalyticsQuerySerializer,
    OverviewAnalyticsQuerySerializer,
)


class OpenedXAnalyticsViewSet(viewsets.ViewSet):
    """
    Analytics endpoints for Open edX courses.

    These endpoints require an authenticated user who is allowed to inspect the
    target course analytics according to the configured permission classes.
    """
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated, IsAdminOrCourseStaff]

    @staticmethod
    def _validated(serializer_class, data):
        serializer = serializer_class(data=data)
        if not serializer.is_valid():
            return None, serializer_error_response(serializer)
        return serializer.validated_data, None

    @action(detail=False, methods=['get'], url_path='overview')
    def analytics_overview(self, request):
        """Return overview analytics for a specific course or the platform."""
        data, error = self._validated(OverviewAnalyticsQuerySerializer, request.query_params)
        if error:
            return error
        result = get_overview_analytics_logic(data.get('course_id'))
        return logic_result_response(result)

    @action(detail=False, methods=['get'], url_path='enrollments')
    def analytics_enrollments(self, request):
        """Return enrollment analytics for a specific course."""
        data, error = self._validated(CourseScopedAnalyticsQuerySerializer, request.query_params)
        if error:
            return error
        result = get_enrollments_analytics_logic(data.get('course_id'))
        return logic_result_response(result)

    @action(detail=False, methods=['get'], url_path='discussions')
    def analytics_discussions(self, request):
        """Return discussion analytics and configuration for a specific course."""
        data, error = self._validated(CourseScopedAnalyticsQuerySerializer, request.query_params)
        if error:
            return error
        result = get_discussions_analytics_logic(data.get('course_id'))
        return logic_result_response(result)

    @action(detail=False, methods=['get'], url_path='detailed')
    def analytics_detailed(self, request):
        """Return a combined detailed analytics view for a specific course."""
        data, error = self._validated(CourseScopedAnalyticsQuerySerializer, request.query_params)
        if error:
            return error
        result = get_detailed_analytics_logic(data.get('course_id'))
        return logic_result_response(result)
