"""
Tools Layer - MCP tools for OpenedX
"""
import json
import logging
from datetime import datetime, timedelta

from common.djangoapps.course_modes.models import CourseMode
from common.djangoapps.student.models import CourseEnrollment, CourseEnrollmentAttribute
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.discussions.models import DiscussionsConfiguration, DiscussionTopicLink
from openedx.core.djangoapps.enrollments.data import get_course_enrollment_info
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.exceptions import DuplicateCourseError

logger = logging.getLogger(__name__)

User = get_user_model()


def get_overview_analytics_logic(course_id: str = None):
    """Estadísticas generales usando CourseOverview y CourseEnrollment"""
    try:
        if course_id:
            course_key = CourseKey.from_string(course_id)
            course = CourseOverview.get_from_id(course_key)

            # Usar el manager personalizado para conteos eficientes
            enrollment_counts = CourseEnrollment.objects.enrollment_counts(course_key)

            # Configuración de discusiones
            discussions_config = DiscussionsConfiguration.get(course_key)

            return {
                "course_id": str(course_key),
                "course_name": course.display_name,
                "course_org": course.org,
                "enrollment_stats": {
                    "total_enrollments": enrollment_counts.get('total', 0),
                    "enrollment_by_mode": enrollment_counts,
                    "is_course_full": CourseEnrollment.objects.is_course_full(course),
                },
                "course_status": {
                    "has_started": course.has_started(),
                    "has_ended": course.has_ended(),
                    "is_enrollment_open": course.is_enrollment_open(),
                    "visible_to_staff_only": course.visible_to_staff_only,
                },
                "discussions": {
                    "enabled": discussions_config.enabled,
                    "provider": discussions_config.provider_type,
                    "in_context_enabled": discussions_config.enable_in_context,
                }
            }
        else:
            # Estadísticas de todos los cursos
            all_courses = CourseOverview.get_all_courses()
            total_enrollments = CourseEnrollment.objects.filter(is_active=True).count()

            return {
                "platform_overview": {
                    "total_courses": all_courses.count(),
                    "total_active_enrollments": total_enrollments,
                },
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"error": f"Error getting overview analytics: {str(e)}"}


def get_enrollments_analytics_logic(course_id: str):
    """Analíticas detalladas de inscripciones usando enrollments.data APIs"""
    try:
        if not course_id:
            return {"error": "course_id is required for enrollment analytics"}

        course_key = CourseKey.from_string(course_id)
        course = CourseOverview.get_from_id(course_key)

        # Usar APIs de enrollments.data para datos consistentes
        enrollment_info = get_course_enrollment_info(str(course_key))

        # Conteos detallados usando el manager personalizado
        enrollment_counts = CourseEnrollment.objects.enrollment_counts(course_key)

        # Análisis temporal
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        enrollments = CourseEnrollment.objects.filter(course_id=course_key)
        recent_enrollments = enrollments.filter(created__gte=last_30_days).count()

        # Atributos de inscripción
        enrollment_attributes = CourseEnrollmentAttribute.objects.filter(
            enrollment__course_id=course_key
        ).values('namespace', 'name').annotate(count=Count('id'))

        return {
            "course_id": str(course_key),
            "course_name": course.display_name,
            "enrollment_summary": {
                "total_enrollments": enrollment_counts.get('total', 0),
                "recent_enrollments_30d": recent_enrollments,
                "enrollment_by_mode": enrollment_counts,
            },
            "course_details": enrollment_info,
            "enrollment_attributes": list(enrollment_attributes),
            "course_limits": {
                "max_enrollments": course.max_student_enrollments_allowed,
                "is_course_full": CourseEnrollment.objects.is_course_full(course),
            },
        }
    except Exception as e:
        return {"error": f"Error getting enrollment analytics: {str(e)}"}


def get_discussions_analytics_logic(course_id: str):
    """Analíticas de discusiones usando discussions.models"""
    try:
        if not course_id:
            return {"error": "course_id is required for discussions analytics"}

        course_key = CourseKey.from_string(course_id)
        course = CourseOverview.get_from_id(course_key)

        # Configuración de discusiones
        discussions_config = DiscussionsConfiguration.get(course_key)

        # Enlaces de temas de discusión
        discussion_topics = DiscussionTopicLink.objects.filter(context_key=course_key)
        enabled_topics = discussion_topics.filter(enabled_in_context=True).count()

        return {
            "course_id": str(course_key),
            "course_name": course.display_name,
            "discussions_configuration": {
                "enabled": discussions_config.enabled,
                "provider_type": discussions_config.provider_type,
                "posting_restrictions": discussions_config.posting_restrictions,
                "enable_in_context": discussions_config.enable_in_context,
                "supports_lti": discussions_config.supports_lti(),
            },
            "topics_summary": {
                "total_topics": discussion_topics.count(),
                "enabled_topics": enabled_topics,
                "disabled_topics": discussion_topics.count() - enabled_topics,
            },
        }
    except Exception as e:
        return {"error": f"Error getting discussions analytics: {str(e)}"}


def get_detailed_analytics_logic(course_id: str):
    """Análisis completo combinando múltiples APIs"""
    try:
        if not course_id:
            return {"error": "course_id is required for detailed analytics"}

        course_key = CourseKey.from_string(course_id)
        course = CourseOverview.get_from_id(course_key)

        # Datos de inscripciones usando APIs especializadas
        enrollment_counts = CourseEnrollment.objects.enrollment_counts(course_key)

        # Modos de curso usando CourseMode API
        available_modes = CourseMode.modes_for_course(course_key)
        modes_info = [
            {
                "slug": mode.slug,
                # "name": mode.mode_display_name,
                "min_price": mode.min_price,
                "currency": mode.currency,
            }
            for mode in available_modes
        ]

        # Configuración de discusiones
        discussions_config = DiscussionsConfiguration.get(course_key)

        return {
            "course_id": str(course_key),
            "course_name": course.display_name,
            "comprehensive_summary": {
                "course_info": {
                    "org": course.org,
                    "number": course.display_number_with_default,
                    "run": course.id.run,
                    "start": course.start.isoformat() if course.start else None,
                    "end": course.end.isoformat() if course.end else None,
                    "self_paced": course.self_paced,
                },
                "enrollment_analytics": {
                    "total": enrollment_counts.get('total', 0),
                    "by_mode": enrollment_counts,
                },
                "course_modes": modes_info,
                "discussions_setup": {
                    "enabled": discussions_config.enabled,
                    "provider": discussions_config.provider_type,
                },
                "operational_status": {
                    "enrollment_open": course.is_enrollment_open(),
                    "course_started": course.has_started(),
                    "course_ended": course.has_ended(),
                    "is_full": CourseEnrollment.objects.is_course_full(course),
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": f"Error getting detailed analytics: {str(e)}"}
