"""
URLs for openedx_owly_apis.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from openedx_owly_apis.views.v1.analytics import OpenedXAnalyticsViewSet
from openedx_owly_apis.views.v1.config_openedx import OpenedXConfigViewSet
from openedx_owly_apis.views.v1.courses import OpenedXCourseViewSet
from openedx_owly_apis.views.v1.roles import OpenedXRolesViewSet

router = DefaultRouter()
router.register(r'owly-analytics', OpenedXAnalyticsViewSet, basename='owly-analytics')
router.register(r'owly-courses', OpenedXCourseViewSet, basename='owly-courses')
router.register(r'owly-roles', OpenedXRolesViewSet, basename='owly-roles')
router.register(r'owly-config', OpenedXConfigViewSet, basename='owly-config')


urlpatterns = [
    path('v1/', include(router.urls)),
    path('v2/', include('openedx_owly_apis.views.v2.urls')),
]
