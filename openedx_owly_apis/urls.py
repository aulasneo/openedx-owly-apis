"""
URLs for openedx_owly_apis.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from openedx_owly_apis.views.analytics import OpenedXAnalyticsViewSet
from openedx_owly_apis.views.courses import OpenedXCourseViewSet
from openedx_owly_apis.views.roles import OpenedXRolesViewSet

router = DefaultRouter()
router.register(r'owly-analytics', OpenedXAnalyticsViewSet, basename='owly-analytics')
router.register(r'owly-courses', OpenedXCourseViewSet, basename='owly-courses')
router.register(r'owly-roles', OpenedXRolesViewSet, basename='owly-roles')


urlpatterns = [
    path('', include(router.urls)),
]
