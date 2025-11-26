from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContentGroupViewSet, ContentGroupCohortAssignmentViewSet

# Create router for v2 API endpoints
router = DefaultRouter()
router.register(r'content-groups', ContentGroupViewSet, basename='content-groups')
router.register(r'content-group-assignments', ContentGroupCohortAssignmentViewSet, basename='content-group-assignments')

urlpatterns = [
    path('', include(router.urls)),
]
