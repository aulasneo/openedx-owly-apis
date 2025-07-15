"""
Tools Layer - MCP tools for OpenedX
"""
import json
import logging
from datetime import datetime, timedelta

from django.db.models import Count
from django.utils import timezone
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.discussions.models import DiscussionsConfiguration
from openedx.core.djangoapps.discussions.models import DiscussionsConfiguration

from openedx.core.djangoapps.enrollments.data import get_course_enrollment_info
from openedx.core.djangoapps.discussions.models import (
    DiscussionsConfiguration,
    DiscussionTopicLink
)

from common.djangoapps.student.models import CourseEnrollmentAttribute
from common.djangoapps.course_modes.models import CourseMode
from common.djangoapps.student.models import CourseEnrollment

from django.contrib.auth import get_user_model

# Imports necesarios
from cms.djangoapps.contentstore.views.course import create_new_course_in_store

from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.exceptions import DuplicateCourseError
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

User = get_user_model()


async def create_course_logic(org: str, course_number: str, run: str,
                              display_name: str, start_date: str = None) -> str:
    """Crea un nuevo curso usando create_new_course_in_store"""

    @sync_to_async
    def create_course_in_db():
        try:
            # Import the official Open edX course creation function
            from cms.djangoapps.contentstore.views.course import create_new_course_in_store
            from xmodule.modulestore import ModuleStoreEnum
            from django.contrib.auth import get_user_model
            from datetime import datetime

            User = get_user_model()

            # Prepare fields
            fields = {}
            if start_date:
                try:
                    fields['start'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    logger.info(f"Invalid start_date format: {start_date}")

            if display_name:
                fields['display_name'] = display_name

            # Get admin user (in Tutor, there should be superuser)
            admin_user = User.objects.filter(is_superuser=True).first()

            # This is the RIGHT approach for Tutor!
            new_course = create_new_course_in_store(
                ModuleStoreEnum.Type.split,
                admin_user,
                org,
                course_number,
                run,
                fields
            )

            logger.info(f"Successfully created course via create_new_course_in_store: {new_course.id}")

            return {
                "success": True,
                "method": "create_new_course_in_store",
                "course_created": {
                    "course_id": str(new_course.id),
                    "display_name": new_course.display_name,
                    "org": new_course.org,
                    "number": new_course.display_number_with_default,
                    "run": new_course.id.run,
                    "created_by": admin_user.username,
                    "studio_url": f"/course/{new_course.id}",
                    "lms_url": f"/courses/{new_course.id}/about"
                }
            }

        except DuplicateCourseError as e:
            logger.info(f"Course already exists: {e}")
            return {
                "success": False,
                "error": "duplicate_course",
                "message": f"Course {org}+{course_number}+{run} already exists"
            }
        except Exception as e:
            logger.exception(f"Course creation failed: {e}")
            return {
                "success": False,
                "error": "creation_failed",
                "message": str(e),
                "troubleshooting": {
                    "check_database": "Verify MongoDB container is accessible",
                    "check_settings": "Ensure Django settings match CMS",
                    "check_permissions": "Verify admin user permissions"
                }
            }


def extract_section_number(name: str) -> str:
    """Extrae número de una cadena de texto"""
    import re
    match = re.search(r'(\d+)', name)
    return match.group(1) if match else None


def sync_xblock_structure(parent, store, admin_user, category, desired_items, edit=False):
    """Sincroniza estructura: agrega faltantes, actualiza existentes"""
    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock

    def find_existing_by_name_or_number(name, children):
        target_number = extract_section_number(name)
        for child in children:
            item = store.get_item(child)
            item_name = item.display_name
            item_number = extract_section_number(item_name)
            if (item_name == name or (target_number and item_number == target_number)):
                return item
        return None

    results = []
    for desired_item in desired_items:
        name = desired_item['name']
        existing = find_existing_by_name_or_number(name, parent.children)

        if existing:
            # ACTUALIZAR nombre si cambió
            if existing.display_name != name:
                existing.display_name = name
                store.update_item(existing, admin_user.id)
                logger.info(f"Updated {category} name: {existing.display_name} -> {name}")
            results.append((existing, desired_item))
        else:
            # CREAR nuevo si no existe (siempre en modo edit, o si es creación inicial)
            new_item = create_xblock(
                parent_locator=str(parent.location),
                user=admin_user,
                category=category,
                display_name=name
            )
            logger.info(f"Created new {category}: {name}")
            results.append((new_item, desired_item))

    return results


async def create_course_structure_logic(course_id: str, units_config: dict, edit: bool = False):
    """Crea/edita la estructura completa del curso: chapters, sequentials y verticals con sincronización inteligente"""

    @sync_to_async
    def create_structure_in_db():
        from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
        from opaque_keys.edx.keys import CourseKey
        from django.contrib.auth import get_user_model
        from xmodule.modulestore.django import modulestore

        try:
            User = get_user_model()
            course_key = CourseKey.from_string(course_id)
            admin_user = User.objects.filter(is_superuser=True).first()

            if not admin_user:
                logger.error("No admin user found")
                return {"error": "No admin user found"}

            store = modulestore()
            course = store.get_course(course_key)

            if not course:
                logger.error(f"Course not found: {course_id}")
                return {"error": f"Course not found: {course_id}"}

            course_locator = str(course.location)
            created_structure = []

            # 1. Sincronizar Chapters usando la nueva lógica
            chapter_results = sync_xblock_structure(
                parent=course,
                store=store,
                admin_user=admin_user,
                category='chapter',
                desired_items=units_config.get('units', []),
                edit=edit
            )

            for chapter, unit_config in chapter_results:
                subsections = []

                # 2. Determinar configuración de subsecciones
                if 'subsections_list' in unit_config:
                    # Sincronizar subsecciones específicas
                    subsection_results = sync_xblock_structure(
                        parent=chapter,
                        store=store,
                        admin_user=admin_user,
                        category='sequential',
                        desired_items=unit_config['subsections_list'],
                        edit=edit
                    )

                    for subsection, subsection_info in subsection_results:
                        verticals = []
                        if 'verticals_list' in subsection_info:
                            # Sincronizar verticals específicos
                            vertical_results = sync_xblock_structure(
                                parent=subsection,
                                store=store,
                                admin_user=admin_user,
                                category='vertical',
                                desired_items=subsection_info['verticals_list'],
                                edit=edit
                            )

                            for vertical, vertical_info in vertical_results:
                                verticals.append({
                                    'vertical_id': str(vertical.location),
                                    'vertical_name': vertical_info['name']
                                })

                        subsections.append({
                            'subsection_id': str(subsection.location),
                            'subsection_name': subsection_info['name'],
                            'verticals': verticals
                        })

                else:
                    # Generar subsecciones genéricas
                    num_subsections = unit_config.get('subsections', 1)
                    verticals_per_subsection = unit_config.get('verticals_per_subsection', 2)

                    generic_subsections = [
                        {'name': f"Subsección {i + 1}"} for i in range(num_subsections)
                    ]

                    subsection_results = sync_xblock_structure(
                        parent=chapter,
                        store=store,
                        admin_user=admin_user,
                        category='sequential',
                        desired_items=generic_subsections,
                        edit=edit
                    )

                    for subsection, subsection_info in subsection_results:
                        generic_verticals = [
                            {'name': f"Unidad {j + 1}"} for j in range(verticals_per_subsection)
                        ]

                        vertical_results = sync_xblock_structure(
                            parent=subsection,
                            store=store,
                            admin_user=admin_user,
                            category='vertical',
                            desired_items=generic_verticals,
                            edit=edit
                        )

                        verticals = [
                            {
                                'vertical_id': str(vertical.location),
                                'vertical_name': vertical_info['name']
                            }
                            for vertical, vertical_info in vertical_results
                        ]

                        subsections.append({
                            'subsection_id': str(subsection.location),
                            'subsection_name': subsection_info['name'],
                            'verticals': verticals
                        })

                created_structure.append({
                    'chapter_id': str(chapter.location),
                    'chapter_name': unit_config['name'],
                    'subsections': subsections
                })

            return {
                "success": True,
                "course_id": course_id,
                "edit_mode": edit,
                "created_structure": created_structure
            }

        except Exception as e:
            logger.exception(f"Exception in course structure creation: {e}")
            return {
                "success": False,
                "error": str(e),
                "course_id": course_id
            }


async def add_discussion_content_logic(vertical_id: str, discussion_config: dict):
    """Add discussion content component to a vertical"""

    @sync_to_async
    def create_discussion_in_db():
        from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
        from django.contrib.auth import get_user_model
        from xmodule.modulestore.django import modulestore

        try:
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()

            if not admin_user:
                return {"success": False, "error": "No admin user found"}

            # Preparar metadata para discussion component
            metadata = {
                'display_name': discussion_config.get('display_name', discussion_config.get('title', 'Discussion'))
            }

            component = create_xblock(
                parent_locator=vertical_id,
                user=admin_user,
                category='discussion',
                display_name=metadata['display_name']
            )

            # Configurar campos específicos de discussion
            store = modulestore()

            # Configurar categoría de discusión
            if 'discussion_category' in discussion_config:
                component.discussion_category = discussion_config['discussion_category']

            # Configurar target/subcategoría de discusión
            if 'discussion_target' in discussion_config:
                component.discussion_target = discussion_config['discussion_target']

            store.update_item(component, admin_user.id)

            return {"success": True, "component_id": str(component.location)}

        except Exception as e:
            logger.exception(f"Error creating discussion content: {e}")
            return {"success": False, "error": str(e)}


async def add_problem_content_logic(vertical_id: str, problem_config: dict):
    """Add problem content component to a vertical"""

    @sync_to_async
    def create_problem_in_db():
        from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
        from django.contrib.auth import get_user_model
        from xmodule.modulestore.django import modulestore

        try:
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()

            if not admin_user:
                return {"success": False, "error": "No admin user found"}

            # Preparar metadata para problem component
            metadata = {
                'display_name': problem_config.get('display_name', problem_config.get('title', 'Problem'))
            }

            # Determinar el tipo de plantilla a usar
            problem_type = problem_config.get('problem_type', 'multiple_choice')
            boilerplate = None

            if problem_type == 'multiple_choice':
                boilerplate = 'multiplechoice'
            elif problem_type == 'blank':
                boilerplate = 'blank_common'

            component = create_xblock(
                parent_locator=vertical_id,
                user=admin_user,
                category='problem',
                display_name=metadata['display_name'],
                boilerplate=boilerplate
            )

            # Si se proporciona contenido personalizado del problema
            if 'data' in problem_config:
                component.data = problem_config['data']
            elif problem_type == 'multiple_choice' and 'question' in problem_config:
                # Generar XML para múltiple choice
                question = problem_config.get('question', 'Question text')
                options = problem_config.get('options', ['Option A', 'Option B'])
                correct_answer = problem_config.get('correct_answer', options[0] if options else 'Option A')
                explanation = problem_config.get('explanation', '')

                choices_xml = ''
                for option in options:
                    is_correct = 'true' if option == correct_answer else 'false'
                    choices_xml += f'<choice correct="{is_correct}">{option}</choice>\n                    '

                problem_xml = f'''<problem>
    <multiplechoiceresponse>
        <label>{question}</label>
        <choicegroup>
            {choices_xml.strip()}
        </choicegroup>
    </multiplechoiceresponse>
</problem>'''

                component.data = problem_xml

            # Configurar peso del problema si se proporciona
            if 'weight' in problem_config:
                component.weight = problem_config['weight']

            # Configurar intentos máximos si se proporciona
            if 'max_attempts' in problem_config:
                component.max_attempts = problem_config['max_attempts']

            store = modulestore()
            store.update_item(component, admin_user.id)

            return {"success": True, "component_id": str(component.location)}

        except Exception as e:
            logger.exception(f"Error creating problem content: {e}")
            return {"success": False, "error": str(e)}


async def add_video_content_logic(vertical_id: str, video_config: dict):
    """Add video content component to a vertical"""

    @sync_to_async
    def create_video_in_db():
        from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
        from django.contrib.auth import get_user_model
        from xmodule.modulestore.django import modulestore

        try:
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()

            if not admin_user:
                return {"success": False, "error": "No admin user found"}

            # Preparar metadata para video component
            metadata = {
                'display_name': video_config.get('display_name', video_config.get('title', 'Video Content'))
            }

            component = create_xblock(
                parent_locator=vertical_id,
                user=admin_user,
                category='video',
                display_name=metadata['display_name']
            )

            # Configurar campos específicos del video
            store = modulestore()

            # Configurar URL del video si se proporciona
            if 'video_url' in video_config:
                video_url = video_config['video_url']
                # Para videos no-YouTube, usar html5_sources
                if not ('youtube.com' in video_url or 'youtu.be' in video_url):
                    component.html5_sources = [video_url]
                else:
                    # Extraer YouTube ID si es un enlace de YouTube
                    import re
                    youtube_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
                    if youtube_match:
                        component.youtube_id_1_0 = youtube_match.group(1)

            # Configurar transcripción si se proporciona
            if 'transcript' in video_config:
                component.sub = video_config['transcript']
                component.show_captions = True
                component.download_track = True

            # Configurar otras opciones de video
            if 'download_video' in video_config:
                component.download_video = video_config['download_video']

            store.update_item(component, admin_user.id)

            return {"success": True, "component_id": str(component.location)}

        except Exception as e:
            logger.exception(f"Error creating video content: {e}")
            return {"success": False, "error": str(e)}


async def add_html_content_logic(vertical_id: str, html_config: dict):
    """Add HTML content component to a vertical"""

    @sync_to_async
    def create_html_in_db():
        from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
        from django.contrib.auth import get_user_model

        try:
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()

            if not admin_user:
                return {"success": False, "error": "No admin user found"}

            # Preparar metadata para HTML component
            metadata = {
                'display_name': html_config.get('display_name', html_config.get('title', 'HTML Content'))
            }

            # Preparar data con el contenido HTML
            data = html_config.get('content', '<p>Default HTML content</p>')

            component = create_xblock(
                parent_locator=vertical_id,
                user=admin_user,
                category='html',
                display_name=metadata['display_name']
            )

            # Actualizar el contenido del componente
            if data:
                component.data = data
                from xmodule.modulestore.django import modulestore
                store = modulestore()
                store.update_item(component, admin_user.id)

            return {"success": True, "component_id": str(component.location)}

        except Exception as e:
            logger.exception(f"Error creating HTML content: {e}")
            return {"success": False, "error": str(e)}
