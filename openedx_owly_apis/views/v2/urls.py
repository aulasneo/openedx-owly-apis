from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import GradeViewSet

# Create router for v2 API endpoints
router = DefaultRouter()
router.register(r'grades', GradeViewSet, basename='grades')

# Custom URL pattern to handle special characters in grade IDs
urlpatterns = [
    # Custom pattern for DELETE with special characters
    re_path(
        r'^grades/(?P<pk>[^/]+)/$',
        GradeViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='grade-detail'
    ),
    # Include default router patterns
    path('', include(router.urls)),
]
