"""
Tools Layer - MCP tools for OpenedX
"""
import json
import logging
from datetime import datetime, timedelta

from django.db.models import Count
from django.db import transaction
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

# Imports necesarios - lazy import to avoid SearchAccess model conflict
# from cms.djangoapps.contentstore.views.course import create_new_course_in_store

from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.exceptions import DuplicateCourseError
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

User = get_user_model()


def _resolve_user(user_identifier):
    """Resolve a user by id, username, or email. Returns User or None."""
    try:
        if user_identifier is None:
            return None
        # Numeric id
        if isinstance(user_identifier, int) or (isinstance(user_identifier, str) and user_identifier.isdigit()):
            return User.objects.filter(id=int(user_identifier)).first()
        # Email
        if isinstance(user_identifier, str) and "@" in user_identifier:
            return User.objects.filter(email__iexact=user_identifier).first()
        # Username
        return User.objects.filter(username=user_identifier).first()
    except Exception:  # pragma: no cover - best effort
        logger.exception("_resolve_user failed")
        return None


def _get_acting_user(user_identifier):
    """Get acting user. Prefer provided identifier; fallback to superuser with warning."""
    user = _resolve_user(user_identifier)
    if user:
        return user
    # Fallback for backward compatibility
    fallback = User.objects.filter(is_superuser=True).first()
    if not fallback:
        return None
    logger.warning(
        "No matching user for identifier '%s'. Falling back to superuser '%s' (id=%s)",
        user_identifier,
        fallback.username,
        fallback.id,
    )
    return fallback


def _validate_vertical_id(vertical_id):
    """Validate vertical_id string and fetch parent item.

    Returns tuple: (store, parent_item, usage_key_str, error_dict_or_none)
    """
    from xmodule.modulestore.django import modulestore
    try:
        from opaque_keys.edx.keys import UsageKey
    except Exception:  # pragma: no cover
        UsageKey = None

    if not vertical_id:
        return None, None, None, {
            "success": False,
            "error": "invalid_vertical_id",
            "message": "vertical_id is required",
        }

    # Try to parse the usage key
    try:
        if UsageKey is None:
            raise ValueError("opaque_keys UsageKey not available")
        usage_key = UsageKey.from_string(str(vertical_id))
    except Exception as e:
        logger.error("vertical_id parse failed: %s | raw=%s", str(e), vertical_id)
        return None, None, None, {
            "success": False,
            "error": "invalid_vertical_id_format",
            "message": f"vertical_id must be a full UsageKey (e.g., block-v1:ORG+NUM+RUN+type@vertical+block@GUID). Got: {vertical_id}",
        }

    store = modulestore()
    try:
        parent_item = store.get_item(usage_key)
    except Exception as e:
        logger.error("modulestore.get_item failed for %s: %s", str(usage_key), str(e))
        return store, None, str(usage_key), {
            "success": False,
            "error": "vertical_not_found",
            "message": f"No item found for vertical_id: {vertical_id}",
        }

    if not parent_item:
        return store, None, str(usage_key), {
            "success": False,
            "error": "vertical_not_found",
            "message": f"No item found for vertical_id: {vertical_id}",
        }

    if getattr(parent_item, 'category', None) != 'vertical':
        return store, parent_item, str(usage_key), {
            "success": False,
            "error": "invalid_parent_category",
            "message": f"Parent category is '{getattr(parent_item, 'category', None)}', expected 'vertical'",
        }

    return store, parent_item, str(usage_key), None


def create_course_logic(org: str, course_number: str, run: str,
                        display_name: str, start_date: str = None,
                        user_identifier=None) -> dict:
    """Crea un nuevo curso usando create_new_course_in_store"""

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

        # Get acting user (requesting user or superuser fallback)
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            logger.error("No acting user available for course creation. identifier=%s", user_identifier)
            return {"success": False, "error": "no_user", "message": "No acting user available"}

        # This is the RIGHT approach for Tutor!
        new_course = create_new_course_in_store(
            ModuleStoreEnum.Type.split,
            acting_user,
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
                "created_by": acting_user.username,
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
            },
            "requested_by": str(user_identifier)
        }


def extract_section_number(name: str) -> str:
    """Extrae número de una cadena de texto"""
    import re
    match = re.search(r'(\d+)', name)
    return match.group(1) if match else None


@transaction.atomic
def sync_xblock_structure(parent, store, acting_user, category, desired_items, edit=False):
    """Sincroniza estructura: agrega faltantes, actualiza existentes"""
    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.db import transaction

    def find_existing_by_name_or_number(name, children):
        target_number = extract_section_number(name)
        for child in children:
            item = store.get_item(child)
            item_name = item.display_name
            item_number = extract_section_number(item_name)
            if (item_name == name or (target_number and item_number == target_number)):
                return item
        return None

    logger.info(
        "sync_xblock_structure start category=%s parent=%s desired_count=%s edit=%s acting_user=%s",
        category, str(getattr(parent, 'location', None)), len(desired_items or []), edit, getattr(acting_user, 'username', None)
    )
    results = []
    items_to_update = []

    # Primero, recolectar todos los items que necesitan actualización
    for desired_item in desired_items:
        name = desired_item['name']
        existing = find_existing_by_name_or_number(name, parent.children)

        if existing:
            # ACTUALIZAR nombre si cambió
            if existing.display_name != name:
                existing.display_name = name
                items_to_update.append((existing, name))
            results.append((existing, desired_item))
        else:
            # CREAR nuevo si no existe (siempre en modo edit, o si es creación inicial)
            new_item = create_xblock(
                parent_locator=str(parent.location),
                user=acting_user,
                category=category,
                display_name=name
            )
            logger.info(f"Created new {category}: {name}")
            results.append((new_item, desired_item))

    # Ahora actualizar todos los items en una sola transacción
    if items_to_update:
        try:
            with transaction.atomic():
                for item, new_name in items_to_update:
                    store.update_item(item, acting_user.id)
                    logger.info(f"Updated {category} name: {item.display_name} -> {new_name}")
        except Exception as e:
            logger.error(f"Error updating {category} items in batch: {str(e)}")
            # Fallback: intentar actualizar uno por uno con delay
            import time
            for item, new_name in items_to_update:
                try:
                    store.update_item(item, acting_user.id)
                    logger.info(f"Updated {category} name (fallback): {item.display_name} -> {new_name}")
                    time.sleep(0.1)  # Small delay to reduce contention
                except Exception as fallback_error:
                    logger.error(f"Failed to update {category} {new_name}: {str(fallback_error)}")

    return results


def create_course_structure_logic(course_id: str, units_config: dict, edit: bool = False, user_identifier=None):
    """Crea/edita la estructura completa del curso: chapters, sequentials y verticals con sincronización inteligente"""

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from opaque_keys.edx.keys import CourseKey
    from django.contrib.auth import get_user_model
    from xmodule.modulestore.django import modulestore

    try:
        User = get_user_model()
        course_key = CourseKey.from_string(course_id)
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            logger.error("No acting user available for structure creation. identifier=%s", user_identifier)
            return {"error": "No acting user available"}

        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            logger.error(f"Course not found: {course_id}")
            return {"error": f"Course not found: {course_id}"}

        course_locator = str(course.location)
        created_structure = []

        logger.info(
            "create_course_structure start course_id=%s edit=%s acting_user=%s units_top=%s",
            course_id, edit, getattr(acting_user, 'username', None), len(units_config.get('units', [])) if units_config else 0
        )

        # 1. Sincronizar Chapters usando la nueva lógica
        chapter_results = sync_xblock_structure(
            parent=course,
            store=store,
            acting_user=acting_user,
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
                    acting_user=acting_user,
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
                            acting_user=acting_user,
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
                    acting_user=acting_user,
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
                        acting_user=acting_user,
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
            "course_id": course_id,
            "requested_by": str(user_identifier)
        }


def add_discussion_content_logic(vertical_id: str, discussion_config: dict, user_identifier=None):
    """Add discussion content component to a vertical"""

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.contrib.auth import get_user_model
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "add_discussion_content start vertical_id=%s requested_by=%s payload_keys=%s",
            vertical_id, str(user_identifier), list((discussion_config or {}).keys())
        )
        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        store, parent_item, usage_key_str, err = _validate_vertical_id(vertical_id)
        if err:
            return err

        # Preparar metadata para discussion component
        metadata = {
            'display_name': discussion_config.get('display_name', discussion_config.get('title', 'Discussion'))
        }

        component = create_xblock(
            parent_locator=str(parent_item.location),
            user=acting_user,
            category='discussion',
            display_name=metadata['display_name']
        )

        # Configurar campos específicos de discussion
        # store is already available from validation

        # Configurar categoría de discusión
        if 'discussion_category' in discussion_config:
            component.discussion_category = discussion_config['discussion_category']

        # Configurar target/subcategoría de discusión
        if 'discussion_target' in discussion_config:
            component.discussion_target = discussion_config['discussion_target']

        store.update_item(component, acting_user.id)

        return {"success": True, "component_id": str(component.location), "parent_vertical": usage_key_str}

    except Exception as e:
        logger.exception(f"Error creating discussion content: {e}")
        return {"success": False, "error": str(e), "vertical_id": vertical_id, "requested_by": str(user_identifier)}


def add_problem_content_logic(vertical_id: str, problem_config: dict, user_identifier=None):
    """Add problem content component to a vertical"""

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.contrib.auth import get_user_model
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "add_problem_content start vertical_id=%s requested_by=%s payload_keys=%s",
            vertical_id, str(user_identifier), list((problem_config or {}).keys())
        )
        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        store, parent_item, usage_key_str, err = _validate_vertical_id(vertical_id)
        if err:
            return err

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
            parent_locator=str(parent_item.location),
            user=acting_user,
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

        store.update_item(component, acting_user.id)

        return {"success": True, "component_id": str(component.location), "parent_vertical": usage_key_str}

    except Exception as e:
        logger.exception(f"Error creating problem content: {e}")
        return {"success": False, "error": str(e), "vertical_id": vertical_id, "requested_by": str(user_identifier)}


def add_video_content_logic(vertical_id: str, video_config: dict, user_identifier=None):
    """Add video content component to a vertical"""

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.contrib.auth import get_user_model
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "add_video_content start vertical_id=%s requested_by=%s payload_keys=%s",
            vertical_id, str(user_identifier), list((video_config or {}).keys())
        )
        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        store, parent_item, usage_key_str, err = _validate_vertical_id(vertical_id)
        if err:
            return err

        # Preparar metadata para video component
        metadata = {
            'display_name': video_config.get('display_name', video_config.get('title', 'Video Content'))
        }

        component = create_xblock(
            parent_locator=str(parent_item.location),
            user=acting_user,
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

        store.update_item(component, acting_user.id)

        return {"success": True, "component_id": str(component.location), "parent_vertical": usage_key_str}

    except Exception as e:
        logger.exception(f"Error creating video content: {e}")
        return {"success": False, "error": str(e), "vertical_id": vertical_id, "requested_by": str(user_identifier)}


def add_html_content_logic(vertical_id: str, html_config: dict, user_identifier=None):
    """Add HTML content component to a vertical"""

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.contrib.auth import get_user_model

    try:
        logger.info(
            "add_html_content start vertical_id=%s requested_by=%s payload_keys=%s",
            vertical_id, str(user_identifier), list((html_config or {}).keys())
        )
        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        store, parent_item, usage_key_str, err = _validate_vertical_id(vertical_id)
        if err:
            return err

        # Preparar metadata para HTML component
        metadata = {
            'display_name': html_config.get('display_name', html_config.get('title', 'HTML Content'))
        }

        # Preparar data con el contenido HTML
        data = html_config.get('content', '<p>Default HTML content</p>')

        component = create_xblock(
            parent_locator=str(parent_item.location),
            user=acting_user,
            category='html',
            display_name=metadata['display_name']
        )

        # Actualizar el contenido del componente
        if data:
            component.data = data
            store.update_item(component, acting_user.id)

        return {"success": True, "component_id": str(component.location), "parent_vertical": usage_key_str}

    except Exception as e:
        logger.exception(f"Error creating HTML content: {e}")
        return {"success": False, "error": str(e), "vertical_id": vertical_id, "requested_by": str(user_identifier)}
