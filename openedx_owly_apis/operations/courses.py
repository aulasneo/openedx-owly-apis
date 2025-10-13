"""
Tools Layer - MCP tools for OpenedX
"""
import json
import logging
import re
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from common.djangoapps.course_modes.models import CourseMode
from common.djangoapps.student.models import CourseEnrollment, CourseEnrollmentAttribute
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.discussions.models import DiscussionsConfiguration, DiscussionTopicLink
from openedx.core.djangoapps.enrollments.data import get_course_enrollment_info
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.exceptions import DuplicateCourseError

# Imports necesarios - lazy import to avoid SearchAccess model conflict
# from cms.djangoapps.contentstore.views.course import create_new_course_in_store

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
            "message": (
                f"vertical_id must be a full UsageKey (e.g., "
                f"block-v1:ORG+NUM+RUN+type@vertical+block@GUID). Got: {vertical_id}"
            ),
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
        from datetime import datetime

        from cms.djangoapps.contentstore.views.course import create_new_course_in_store
        from django.contrib.auth import get_user_model
        from xmodule.modulestore import ModuleStoreEnum

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
        category,
        str(getattr(parent, 'location', None)),
        len(desired_items or []),
        edit,
        getattr(acting_user, 'username', None),
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
    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
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
            course_id,
            edit,
            getattr(acting_user, 'username', None),
            len(units_config.get('units', [])) if units_config else 0,
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


def update_course_settings_logic(course_id: str, settings_data: dict, user_identifier=None) -> dict:
    """Update course settings including dates, details, and other configurations"""

    from datetime import datetime

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "update_course_settings start course_id=%s requested_by=%s settings_keys=%s",
            course_id, str(user_identifier), list((settings_data or {}).keys())
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        # Parse course key
        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_course_id",
                "message": f"Invalid course_id format: {course_id}"
            }

        # Get course from modulestore
        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}"
            }

        # Track updated fields
        updated_fields = []

        # Helper function to parse ISO datetime strings with detailed logging
        def parse_datetime(date_str, field_name):
            logger.info(f"Attempting to parse {field_name}: '{date_str}' (type: {type(date_str)})")

            if not date_str:
                logger.info(f"{field_name}: Empty or None value, skipping")
                return None

            try:
                # Handle ISO format with Z or timezone
                original_str = str(date_str)
                if original_str.endswith('Z'):
                    date_str = original_str[:-1] + '+00:00'
                    logger.info(f"{field_name}: Converted Z format: '{original_str}' -> '{date_str}'")

                parsed_date = datetime.fromisoformat(date_str)
                logger.info(f"{field_name}: Successfully parsed to {parsed_date}")
                return parsed_date

            except ValueError as e:
                logger.error(f"{field_name}: Failed to parse datetime '{date_str}', error: {e}")
                return None
            except Exception as e:
                logger.error(f"{field_name}: Unexpected error parsing datetime '{date_str}', error: {e}")
                return None

        # Log all incoming settings data for debugging
        logger.info(f"Received settings_data: {settings_data}")

        # Update course fields based on settings_data with detailed logging
        if 'start_date' in settings_data:
            logger.info(f"Processing start_date field...")
            start_date = parse_datetime(settings_data['start_date'], 'start_date')
            if start_date:
                logger.info(f"Setting course.start = {start_date}")
                course.start = start_date
                updated_fields.append('start_date')
            else:
                logger.warning(f"start_date parsing failed, not updating field")

        if 'end_date' in settings_data:
            logger.info(f"Processing end_date field...")
            end_date = parse_datetime(settings_data['end_date'], 'end_date')
            if end_date:
                logger.info(f"Setting course.end = {end_date}")
                course.end = end_date
                updated_fields.append('end_date')
            else:
                logger.warning(f"end_date parsing failed, not updating field")

        if 'enrollment_start' in settings_data:
            logger.info(f"Processing enrollment_start field...")
            enrollment_start = parse_datetime(settings_data['enrollment_start'], 'enrollment_start')
            if enrollment_start:
                logger.info(f"Setting course.enrollment_start = {enrollment_start}")
                course.enrollment_start = enrollment_start
                updated_fields.append('enrollment_start')
            else:
                logger.warning(f"enrollment_start parsing failed, not updating field")

        if 'enrollment_end' in settings_data:
            logger.info(f"Processing enrollment_end field...")
            enrollment_end = parse_datetime(settings_data['enrollment_end'], 'enrollment_end')
            if enrollment_end:
                logger.info(f"Setting course.enrollment_end = {enrollment_end}")
                course.enrollment_end = enrollment_end
                updated_fields.append('enrollment_end')
            else:
                logger.warning(f"enrollment_end parsing failed, not updating field")

        if 'display_name' in settings_data and settings_data['display_name']:
            course.display_name = settings_data['display_name']
            updated_fields.append('display_name')

        if 'language' in settings_data and settings_data['language']:
            course.language = settings_data['language']
            updated_fields.append('language')

        if 'self_paced' in settings_data:
            course.self_paced = bool(settings_data['self_paced'])
            updated_fields.append('self_paced')

        if 'short_description' in settings_data:
            course.short_description = settings_data['short_description']
            updated_fields.append('short_description')

        if 'overview' in settings_data:
            course.overview = settings_data['overview']
            updated_fields.append('overview')

        if 'effort' in settings_data:
            course.effort = settings_data['effort']
            updated_fields.append('effort')

        if 'course_image_name' in settings_data:
            course.course_image = settings_data['course_image_name']
            updated_fields.append('course_image_name')

        # Save changes to modulestore
        if updated_fields:
            store.update_item(course, acting_user.id)
            logger.info(f"Successfully updated course {course_id} fields: {updated_fields}")

        return {
            "success": True,
            "course_id": course_id,
            "updated_fields": updated_fields,
            "message": (
                f"Successfully updated {len(updated_fields)} field(s)"
                if updated_fields
                else "No fields to update"
            ),
        }

    except Exception as e:
        logger.exception(f"Error updating course settings: {e}")
        return {
            "success": False,
            "error": "update_failed",
            "message": str(e),
            "course_id": course_id,
            "requested_by": str(user_identifier)
        }


def update_advanced_settings_logic(course_id: str, advanced_settings: dict, user_identifier=None) -> dict:
    """Update course advanced settings (other_course_settings)"""

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "update_advanced_settings start course_id=%s requested_by=%s settings_keys=%s",
            course_id, str(user_identifier), list((advanced_settings or {}).keys())
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        # Parse course key
        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_course_id",
                "message": f"Invalid course_id format: {course_id}"
            }

        # Get course from modulestore
        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}"
            }

        # Validate and update advanced settings
        updated_settings = []

        if not advanced_settings:
            return {
                "success": False,
                "error": "no_settings_provided",
                "message": "No advanced settings provided to update"
            }

        # Get current other_course_settings or initialize as empty dict
        current_settings = getattr(course, 'other_course_settings', {}) or {}

        # Update each advanced setting
        for setting_key, setting_value in advanced_settings.items():
            try:
                # Validate setting key format
                if not isinstance(setting_key, str) or not setting_key.strip():
                    logger.warning(f"Invalid setting key: {setting_key}")
                    continue

                # Handle different value types
                if setting_value is None:
                    # Remove setting if value is None
                    if setting_key in current_settings:
                        del current_settings[setting_key]
                        updated_settings.append(f"removed_{setting_key}")
                else:
                    # Update or add setting
                    current_settings[setting_key] = setting_value
                    updated_settings.append(setting_key)

                logger.info(f"Updated advanced setting: {setting_key} = {setting_value}")

            except Exception as setting_error:
                logger.warning(f"Error updating setting {setting_key}: {setting_error}")
                continue

        # Save updated settings back to course
        if updated_settings:
            course.other_course_settings = current_settings
            store.update_item(course, acting_user.id)
            logger.info(f"Successfully updated course {course_id} advanced settings: {updated_settings}")

        return {
            "success": True,
            "course_id": course_id,
            "updated_settings": updated_settings,
            "current_settings": current_settings,
            "message": (
                f"Successfully updated {len(updated_settings)} advanced setting(s)"
                if updated_settings
                else "No settings to update"
            ),
        }

    except Exception as e:
        logger.exception(f"Error updating advanced settings: {e}")
        return {
            "success": False,
            "error": "update_failed",
            "message": str(e),
            "course_id": course_id,
            "requested_by": str(user_identifier)
        }


def enable_configure_certificates_logic(course_id: str, certificate_config: dict, user_identifier=None) -> dict:
    """Enable and configure certificates for a course in OpenEdX"""

    from datetime import datetime

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "enable_configure_certificates start course_id=%s requested_by=%s config_keys=%s",
            course_id, str(user_identifier), list((certificate_config or {}).keys())
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        # Parse course key
        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_course_id",
                "message": f"Invalid course_id format: {course_id}"
            }

        # Get course from modulestore
        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}"
            }

        # Configure certificate settings
        updated_settings = []

        if not certificate_config:
            return {
                "success": False,
                "error": "no_config_provided",
                "message": "No certificate configuration provided"
            }

        # Enable certificates if requested
        if certificate_config.get('enable_certificates', False):
            course.certificates_display_behavior = 'end'
            course.certificate_available_date = None
            updated_settings.append('certificates_enabled')
            logger.info(f"Enabled certificates for course {course_id}")

        # Configure certificate display behavior
        if 'certificates_display_behavior' in certificate_config:
            valid_behaviors = ['end', 'early_with_info', 'early_no_info']
            behavior = certificate_config['certificates_display_behavior']
            if behavior in valid_behaviors:
                course.certificates_display_behavior = behavior
                updated_settings.append('certificates_display_behavior')
                logger.info(f"Set certificate display behavior to: {behavior}")
            else:
                logger.warning(f"Invalid certificate display behavior: {behavior}")

        # Configure certificate available date
        if 'certificate_available_date' in certificate_config:
            from datetime import datetime
            date_str = certificate_config['certificate_available_date']
            if date_str:
                try:
                    if date_str.endswith('Z'):
                        date_str = date_str[:-1] + '+00:00'
                    cert_date = datetime.fromisoformat(date_str)
                    course.certificate_available_date = cert_date
                    updated_settings.append('certificate_available_date')
                    logger.info(f"Set certificate available date to: {cert_date}")
                except ValueError as e:
                    logger.warning(f"Invalid certificate date format: {date_str}, error: {e}")
            else:
                course.certificate_available_date = None
                updated_settings.append('certificate_available_date_cleared')

        # Update advanced settings for certificate configuration
        current_settings = getattr(course, 'other_course_settings', {}) or {}

        # Certificate name (long)
        if 'certificate_name_long' in certificate_config:
            current_settings['cert_name_long'] = certificate_config['certificate_name_long']
            updated_settings.append('certificate_name_long')

        # Certificate name (short)
        if 'certificate_name_short' in certificate_config:
            current_settings['cert_name_short'] = certificate_config['certificate_name_short']
            updated_settings.append('certificate_name_short')

        # Certificate web/html view overrides
        if 'certificate_web_view_overrides' in certificate_config:
            current_settings['cert_html_view_overrides'] = certificate_config['certificate_web_view_overrides']
            updated_settings.append('certificate_web_view_overrides')

        # Update course with new settings
        if updated_settings:
            if current_settings != getattr(course, 'other_course_settings', {}):
                course.other_course_settings = current_settings
            store.update_item(course, acting_user.id)
            logger.info(f"Successfully updated certificate settings for course {course_id}: {updated_settings}")

        # Try to create/configure certificate configuration if needed
        certificate_status = "configured"
        try:
            from lms.djangoapps.certificates.models import CertificateGenerationConfiguration

            # Enable certificate generation globally if not already enabled
            cert_config, created = CertificateGenerationConfiguration.objects.get_or_create(
                defaults={'enabled': True}
            )
            if created or not cert_config.enabled:
                cert_config.enabled = True
                cert_config.save()
                certificate_status = "enabled_globally"
                logger.info("Enabled certificate generation globally")

        except Exception as cert_error:
            logger.warning(f"Could not configure certificate generation: {cert_error}")
            certificate_status = "configured_course_only"

        return {
            "success": True,
            "course_id": course_id,
            "updated_settings": updated_settings,
            "certificate_status": certificate_status,
            "current_config": {
                "certificates_display_behavior": getattr(course, 'certificates_display_behavior', None),
                "certificate_available_date": (
                    getattr(course, 'certificate_available_date', None).isoformat()
                    if getattr(course, 'certificate_available_date', None)
                    else None
                ),
                "certificate_name_long": current_settings.get('cert_name_long'),
                "certificate_name_short": current_settings.get('cert_name_short'),
                "certificate_web_view_overrides": current_settings.get('cert_html_view_overrides')
            },
            "message": (
                f"Successfully configured {len(updated_settings)} certificate setting(s)"
                if updated_settings
                else "No settings to update"
            ),
        }

    except Exception as e:
        logger.exception(f"Error configuring certificates: {e}")
        return {
            "success": False,
            "error": "configuration_failed",
            "message": str(e),
            "course_id": course_id,
            "requested_by": str(user_identifier)
        }


def control_unit_availability_logic(unit_id: str, availability_config: dict, user_identifier=None) -> dict:
    """Control unit availability and due dates in OpenEdX"""

    from datetime import datetime

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import UsageKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "control_unit_availability start unit_id=%s requested_by=%s config_keys=%s",
            unit_id, str(user_identifier), list((availability_config or {}).keys())
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        # Parse unit key
        try:
            unit_key = UsageKey.from_string(unit_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_unit_id",
                "message": f"Invalid unit_id format: {unit_id}"
            }

        # Get unit from modulestore
        store = modulestore()
        unit = store.get_item(unit_key)

        if not unit:
            return {
                "success": False,
                "error": "unit_not_found",
                "message": f"Unit not found: {unit_id}"
            }

        # Validate unit type (should be vertical, sequential, or chapter)
        valid_categories = ['vertical', 'sequential', 'chapter']
        if getattr(unit, 'category', None) not in valid_categories:
            return {
                "success": False,
                "error": "invalid_unit_type",
                "message": (
                    f"Unit category '{getattr(unit, 'category', None)}' is not supported. "
                    f"Must be one of: {valid_categories}"
                ),
            }

        # Configure availability settings
        updated_settings = []

        if not availability_config:
            return {
                "success": False,
                "error": "no_config_provided",
                "message": "No availability configuration provided"
            }

        # Helper function to parse datetime
        def parse_datetime(date_str):
            if not date_str:
                return None
            try:
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                return datetime.fromisoformat(date_str)
            except ValueError as e:
                logger.warning(f"Invalid datetime format: {date_str}, error: {e}")
                return None

        # Set start date (when unit becomes available)
        if 'start_date' in availability_config:
            start_date = parse_datetime(availability_config['start_date'])
            if start_date or availability_config['start_date'] is None:
                unit.start = start_date
                updated_settings.append('start_date')
                logger.info(f"Set start date to: {start_date}")

        # Set due date (when unit is due)
        if 'due_date' in availability_config:
            due_date = parse_datetime(availability_config['due_date'])
            if due_date or availability_config['due_date'] is None:
                unit.due = due_date
                updated_settings.append('due_date')
                logger.info(f"Set due date to: {due_date}")

        # Set visibility to staff only
        if 'visible_to_staff_only' in availability_config:
            visible_to_staff = bool(availability_config['visible_to_staff_only'])
            unit.visible_to_staff_only = visible_to_staff
            updated_settings.append('visible_to_staff_only')
            logger.info(f"Set visible to staff only: {visible_to_staff}")

        # Set graded status (for sequentials)
        if 'graded' in availability_config and getattr(unit, 'category', None) == 'sequential':
            graded = bool(availability_config['graded'])
            unit.graded = graded
            updated_settings.append('graded')
            logger.info(f"Set graded status: {graded}")

        # Set format (for sequentials - homework, exam, etc.)
        if 'format' in availability_config and getattr(unit, 'category', None) == 'sequential':
            format_type = availability_config['format']
            if format_type:
                unit.format = format_type
                updated_settings.append('format')
                logger.info(f"Set format: {format_type}")

        # Set hide after due (for sequentials)
        if 'hide_after_due' in availability_config and getattr(unit, 'category', None) == 'sequential':
            hide_after_due = bool(availability_config['hide_after_due'])
            unit.hide_after_due = hide_after_due
            updated_settings.append('hide_after_due')
            logger.info(f"Set hide after due: {hide_after_due}")

        # Update unit with new settings
        if updated_settings:
            store.update_item(unit, acting_user.id)
            logger.info(
                f"Successfully updated availability settings for unit {unit_id}: {updated_settings}"
            )

            return {
                "success": True,
                "unit_id": unit_id,
                "unit_type": getattr(unit, 'category', None),
                "updated_settings": updated_settings,
                "current_config": {
                    "start_date": getattr(unit, 'start', None).isoformat()
                    if getattr(unit, 'start', None)
                    else None,
                    "due_date": (
                        getattr(unit, 'due', None).isoformat()
                        if getattr(unit, 'due', None)
                        else None
                    ),
                    "visible_to_staff_only": getattr(unit, 'visible_to_staff_only', False),
                    "graded": (
                        getattr(unit, 'graded', False)
                        if getattr(unit, 'category', None) == 'sequential'
                        else None
                    ),
                    "format": (
                        getattr(unit, 'format', None)
                        if getattr(unit, 'category', None) == 'sequential'
                        else None
                    ),
                    "hide_after_due": (
                        getattr(unit, 'hide_after_due', False)
                        if getattr(unit, 'category', None) == 'sequential'
                        else None
                    ),
                },
                "message": (
                    f"Successfully updated {len(updated_settings)} availability setting(s)"
                    if updated_settings
                    else "No settings to update"
                ),
            }

    except Exception as e:
        logger.exception(f"Error controlling unit availability: {e}")
        return {
            "success": False,
            "error": "control_failed",
            "message": str(e),
            "unit_id": unit_id,
            "requested_by": str(user_identifier)
        }


def create_openedx_problem_logic(
    unit_locator: str,
    problem_type: str,
    display_name: str,
    problem_data: dict,
    user_identifier=None,
) -> dict:
    """Create a problem component in an OpenEdX course unit"""

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import UsageKey
    from xblock.core import XBlock
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "create_openedx_problem start unit_locator=%s problem_type=%s requested_by=%s",
            unit_locator, problem_type, str(user_identifier)
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        # Parse unit locator
        try:
            unit_key = UsageKey.from_string(unit_locator)
            logger.info(f"Parsed unit_key successfully: {unit_key}")
        except Exception as e:
            logger.error(f"Failed to parse unit_locator '{unit_locator}': {e}")
            return {
                "success": False,
                "error": "invalid_unit_locator",
                "message": f"Invalid unit_locator format: {unit_locator}. Error: {str(e)}"
            }

        # Get modulestore and unit
        try:
            store = modulestore()
            logger.info(f"Got modulestore: {store}")
            unit = store.get_item(unit_key)
            logger.info(f"Retrieved unit: {unit}")
        except Exception as e:
            logger.error(f"Failed to get modulestore or unit: {e}")
            return {
                "success": False,
                "error": "modulestore_error",
                "message": f"Failed to access modulestore or unit: {str(e)}"
            }

        if not unit:
            logger.error(f"Unit not found for locator: {unit_locator}")
            return {
                "success": False,
                "error": "unit_not_found",
                "message": f"Unit not found: {unit_locator}"
            }

        # Generate problem XML based on type
        try:
            problem_xml = _generate_problem_xml(problem_type, problem_data, display_name)
            logger.info(f"Generated XML for problem type {problem_type}: {problem_xml[:200]}...")
        except Exception as e:
            logger.error(f"Failed to generate XML: {e}")
            return {
                "success": False,
                "error": "xml_generation_failed",
                "message": f"Failed to generate problem XML: {str(e)}"
            }

        # Create new problem XBlock
        try:
            new_problem = store.create_child(
                acting_user.id,
                unit_key,
                "problem",
                block_id=None,
                fields={
                    "display_name": display_name,
                    "data": problem_xml
                }
            )
            logger.info(f"Successfully created problem {new_problem.location} in unit {unit_locator}")
        except Exception as e:
            logger.error(f"Failed to create XBlock: {e}")
            return {
                "success": False,
                "error": "xblock_creation_failed",
                "message": f"Failed to create XBlock: {str(e)}"
            }

        return {
            "success": True,
            "unit_locator": unit_locator,
            "problem_locator": str(new_problem.location),
            "problem_type": problem_type,
            "display_name": display_name,
            "problem_data": problem_data,
            "message": f"Successfully created {problem_type} problem in unit"
        }

    except Exception as e:
        logger.exception(f"Error creating problem: {e}")
        return {
            "success": False,
            "error": "creation_failed",
            "message": str(e),
            "unit_locator": unit_locator,
            "requested_by": str(user_identifier)
        }


def _generate_problem_xml(problem_type: str, problem_data: dict, display_name: str) -> str:
    """Generate XML for different problem types"""

    if problem_type == "multiplechoiceresponse":
        return _generate_multiple_choice_xml(problem_data, display_name)
    elif problem_type == "numericalresponse":
        return _generate_numerical_xml(problem_data, display_name)
    elif problem_type == "stringresponse":
        return _generate_string_response_xml(problem_data, display_name)
    elif problem_type == "choiceresponse":
        return _generate_choice_response_xml(problem_data, display_name)
    elif problem_type == "optionresponse":
        return _generate_dropdown_xml(problem_data, display_name)
    else:
        return _generate_generic_problem_xml(problem_data, display_name)


def _generate_multiple_choice_xml(problem_data: dict, display_name: str) -> str:
    """Generate XML for multiple choice problems"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}

    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Multiple Choice Problem"

    question_text = problem_data.get('question_text', 'Enter your question here')
    question_text = str(question_text) if question_text is not None else 'Enter your question here'

    choices = problem_data.get('choices', [
        {'text': 'Option A', 'correct': True},
        {'text': 'Option B', 'correct': False},
        {'text': 'Option C', 'correct': False}
    ])

    # Ensure we have valid choices
    if not choices or not isinstance(choices, list):
        choices = [
            {'text': 'Option A', 'correct': True},
            {'text': 'Option B', 'correct': False},
            {'text': 'Option C', 'correct': False}
        ]

    # Escape XML special characters - robust handling of None values
    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)

    xml = f'''<problem display_name="{display_name}">
    <multiplechoiceresponse>
        <p>{question_text}</p>
        <choicegroup type="MultipleChoice">'''

    for choice in choices:
        if isinstance(choice, dict):
            # Ensure choice text is not None before processing
            choice_text = choice.get('text', '')
            if choice_text is None:
                choice_text = ''
            choice_text = escape_xml(str(choice_text))
            # ALWAYS include correct attribute - OpenedX requires it on ALL choices
            correct = 'correct="true"' if choice.get('correct', False) else 'correct="false"'
            xml += f'\n            <choice {correct}>{choice_text}</choice>'
        elif isinstance(choice, str):
            # Handle string choices (assume first one is correct by default)
            choice_text = escape_xml(str(choice) if choice is not None else '')
            # ALWAYS include correct attribute - OpenedX requires it on ALL choices
            correct = 'correct="true"' if choices.index(choice) == 0 else 'correct="false"'
            xml += f'\n            <choice {correct}>{choice_text}</choice>'
        else:
            # Handle any other type by converting to string
            choice_text = escape_xml(str(choice) if choice is not None else '')
            # ALWAYS include correct attribute - OpenedX requires it on ALL choices
            xml += f'\n            <choice correct="false">{choice_text}</choice>'

    xml += '''
        </choicegroup>
    </multiplechoiceresponse>
</problem>'''

    return xml


def _generate_numerical_xml(problem_data: dict, display_name: str) -> str:
    """Generate XML for numerical response problems"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}

    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Numerical Problem"

    question_text = problem_data.get('question_text', 'Enter your numerical question here')
    question_text = str(question_text) if question_text is not None else 'Enter your numerical question here'

    correct_answer = problem_data.get('correct_answer', '42')
    correct_answer = str(correct_answer) if correct_answer is not None else '42'

    tolerance = problem_data.get('tolerance', '0.01')
    tolerance = str(tolerance) if tolerance is not None else '0.01'
    # Escape XML special characters

    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)
    correct_answer = escape_xml(correct_answer)
    tolerance = escape_xml(tolerance)

    xml = f'''<problem display_name="{display_name}">
    <numericalresponse answer="{correct_answer}">
        <p>{question_text}</p>
        <responseparam type="tolerance" default="{tolerance}"/>
        <textline size="20"/>
    </numericalresponse>
</problem>'''

    return xml


def _generate_string_response_xml(problem_data: dict, display_name: str) -> str:
    """Generate XML for string response problems"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}

    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Text Problem"

    question_text = problem_data.get('question_text', 'Enter your text question here')
    question_text = str(question_text) if question_text is not None else 'Enter your text question here'
    correct_answer = problem_data.get('correct_answer', 'correct answer')
    correct_answer = str(correct_answer) if correct_answer is not None else 'correct answer'

    case_sensitive = problem_data.get('case_sensitive', False)

    # Escape XML special characters
    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)
    correct_answer = escape_xml(correct_answer)

    type_attr = 'type="ci"' if not case_sensitive else ''

    xml = f'''<problem display_name="{display_name}">
    <stringresponse answer="{correct_answer}" {type_attr}>
        <p>{question_text}</p>
        <textline size="20"/>
    </stringresponse>
</problem>'''

    return xml


def _generate_choice_response_xml(problem_data: dict, display_name: str) -> str:
    """Generate XML for choice response problems (checkboxes/multi-select)"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}

    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Multi-Select Problem"

    question_text = problem_data.get('question_text', 'Select all correct options')
    question_text = str(question_text) if question_text is not None else 'Select all correct options'

    choices = problem_data.get('choices', [
        {'text': 'Option A', 'correct': True},
        {'text': 'Option B', 'correct': False},
        {'text': 'Option C', 'correct': True}
    ])

    # Ensure we have valid choices
    if not choices or not isinstance(choices, list):
        choices = [
            {'text': 'Option A', 'correct': True},
            {'text': 'Option B', 'correct': False},
            {'text': 'Option C', 'correct': True}
        ]

    # Escape XML special characters
    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)

    xml = f'''<problem display_name="{display_name}">
    <choiceresponse>
        <p>{question_text}</p>
        <checkboxgroup>'''

    for choice in choices:
        if isinstance(choice, dict):
            # Ensure choice text is not None before processing
            choice_text = choice.get('text', '')
            if choice_text is None:
                choice_text = ''
            choice_text = escape_xml(str(choice_text))
            correct = 'correct="true"' if choice.get('correct', False) else 'correct="false"'
            xml += f'\n            <choice {correct}>{choice_text}</choice>'
        elif isinstance(choice, str):
            # Handle string choices (assume first one is correct by default)
            choice_text = escape_xml(str(choice) if choice is not None else '')
            correct = 'correct="true"' if choices.index(choice) == 0 else 'correct="false"'
            xml += f'\n            <choice {correct}>{choice_text}</choice>'
        else:
            # Handle any other type by converting to string
            choice_text = escape_xml(str(choice) if choice is not None else '')
            xml += f'\n            <choice correct="false">{choice_text}</choice>'

    xml += '''
        </checkboxgroup>
    </choiceresponse>
</problem>'''

    return xml


def _generate_generic_problem_xml(problem_data: dict, display_name: str) -> str:
    """Generate generic problem XML"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}
    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Generic Problem"

    question_text = problem_data.get('question_text', 'Enter your question here')
    question_text = str(question_text) if question_text is not None else 'Enter your question here'

    # Escape XML special characters
    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)

    xml = f'''<problem display_name="{display_name}">
    <p>{question_text}</p>
    <p>This is a generic problem. Please customize the XML as needed.</p>
</problem>'''

    return xml


def _generate_dropdown_xml(problem_data: dict, display_name: str) -> str:
    """Generate XML for dropdown problems (optionresponse)"""

    # Ensure all inputs are properly validated and not None
    if problem_data is None:
        problem_data = {}

    # Ensure display_name is a valid string
    display_name = str(display_name) if display_name is not None else "New Dropdown Problem"

    question_text = problem_data.get('question_text', 'Select the correct option')
    # Ensure question_text is a valid string
    question_text = str(question_text) if question_text is not None else 'Select the correct option'

    choices = problem_data.get('choices', [
        {'text': 'Option A', 'correct': True},
        {'text': 'Option B', 'correct': False},
        {'text': 'Option C', 'correct': False}
    ])

    # Ensure we have valid choices
    if not choices or not isinstance(choices, list):
        choices = [
            {'text': 'Option A', 'correct': True},
            {'text': 'Option B', 'correct': False},
            {'text': 'Option C', 'correct': False}
        ]

    # Find the correct answer and ensure all choice texts are strings
    correct_answer = None
    for choice in choices:
        if isinstance(choice, dict):
            # Ensure choice text is a valid string
            choice_text = choice.get('text', '')
            choice['text'] = str(choice_text) if choice_text is not None else ''

            if choice.get('correct', False):
                correct_answer = choice['text']

    if not correct_answer:
        correct_answer = choices[0].get('text', 'Option A') if choices else 'Option A'

    # Escape XML special characters to prevent malformed XML
    def escape_xml(text):
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('"', '&quot;').replace("'", '&apos;'))

    display_name = escape_xml(display_name)
    question_text = escape_xml(question_text)

    xml = f'''<problem display_name="{display_name}">
    <optionresponse>
        <p>{question_text}</p>
        <optioninput>'''

    # Add options to dropdown
    for choice in choices:
        if isinstance(choice, dict):
            # Ensure choice text is not None before processing
            choice_text = choice.get('text', '')
            if choice_text is None:
                choice_text = ''
            choice_text = escape_xml(str(choice_text))
            # ALWAYS include correct attribute - OpenedX requires it on ALL options
            correct_attr = ' correct="True"' if choice.get('correct', False) else ' correct="False"'
            xml += f'\n            <option{correct_attr}>{choice_text}</option>'
        elif isinstance(choice, str):
            # Handle string choices (assume first one is correct by default)
            choice_text = escape_xml(str(choice) if choice is not None else '')
            # ALWAYS include correct attribute - OpenedX requires it on ALL options
            correct_attr = ' correct="True"' if choices.index(choice) == 0 else ' correct="False"'
            xml += f'\n            <option{correct_attr}>{choice_text}</option>'
        else:
            # Handle any other type by converting to string
            choice_text = escape_xml(str(choice) if choice is not None else '')
            # ALWAYS include correct attribute - OpenedX requires it on ALL options
            xml += f'\n            <option correct="False">{choice_text}</option>'

    xml += '''
        </optioninput>
    </optionresponse>
</problem>'''

    return xml


def publish_content_logic(content_id: str, publish_type: str = "auto", user_identifier=None) -> dict:
    """
    Publish course content (courses, units, subsections, sections) in OpenEdX.
    Uses a robust approach that handles missing items gracefully.

    Args:
        content_id: OpenEdX content ID (course key or usage key format)
        publish_type: Type of publishing - "auto", "manual", "course", "unit"
        user_identifier: User making the request

    Returns:
        Dict with success status and publishing details
    """
    import logging

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey, UsageKey
    from xmodule.modulestore.django import modulestore
    from xmodule.modulestore.exceptions import ItemNotFoundError

    logger = logging.getLogger(__name__)

    try:
        logger.info(
            "publish_content start content_id=%s publish_type=%s requested_by=%s",
            content_id, publish_type, str(user_identifier)
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {
                "success": False,
                "error": "user_not_found",
                "message": "Valid user required for publishing",
                "content_id": content_id
            }

        store = modulestore()
        published_items = []

        # Determine if this is a course or unit/component
        try:
            # Try parsing as CourseKey first
            course_key = CourseKey.from_string(content_id)
            is_course = True
            logger.info(f"Detected course key: {course_key}")
        except Exception:
            try:
                # Try parsing as UsageKey
                usage_key = UsageKey.from_string(content_id)
                course_key = usage_key.course_key
                is_course = False
                logger.info(f"Detected usage key: {usage_key} for course: {course_key}")
            except Exception as parse_error:
                return {
                    "success": False,
                    "error": "invalid_content_id",
                    "message": f"Invalid content ID format: {parse_error}",
                    "content_id": content_id
                }

        # Get course and validate access
        try:
            course = store.get_course(course_key)
            if not course:
                return {
                    "success": False,
                    "error": "course_not_found",
                    "message": f"Course not found: {course_key}",
                    "content_id": content_id
                }
        except Exception as access_error:
            return {
                "success": False,
                "error": "access_denied",
                "message": f"Access denied or course not found: {access_error}",
                "content_id": content_id,
                "user": acting_user.username
            }

        if is_course or publish_type == "course":
            # Publish entire course by publishing all its children recursively
            try:
                def publish_recursively(item, level=0):
                    """Recursively publish an item and all its children"""
                    published = []
                    item_usage_key = item.location

                    try:
                        store.publish(item_usage_key, acting_user.id)
                        published.append({
                            "type": getattr(item, 'category', 'unknown'),
                            "id": str(item_usage_key),
                            "display_name": getattr(item, 'display_name', 'Unnamed'),
                            "level": level
                        })
                        logger.info(f"Published {item.category}: {item.display_name}")
                    except Exception as pub_error:
                        logger.warning(f"Failed to publish {item_usage_key}: {pub_error}")

                    # Recursively publish children
                    if hasattr(item, 'children'):
                        for child_key in item.children:
                            try:
                                child_item = store.get_item(child_key)
                                published.extend(publish_recursively(child_item, level + 1))
                            except Exception as child_error:
                                logger.warning(f"Failed to get/publish child {child_key}: {child_error}")

                    return published

                # Start recursive publishing from course
                published_items = publish_recursively(course)

                logger.info(f"Successfully published course and {len(published_items)} items")

            except Exception as course_error:
                logger.exception(f"Error publishing course: {course_error}")
                return {
                    "success": False,
                    "error": "course_publish_failed",
                    "message": f"Failed to publish course: {course_error}",
                    "content_id": content_id
                }
        else:
            # Publish specific unit/component using direct approach
            try:
                usage_key = UsageKey.from_string(content_id)
                # Direct publish approach - don't try to get the item first
                try:
                    store.publish(usage_key, acting_user.id)
                    logger.info(f"Successfully published via direct method: {usage_key}")

                    # Try to get details after publishing
                    try:
                        published_item = store.get_item(usage_key)
                        display_name = getattr(published_item, 'display_name', 'Published Item')
                        category = getattr(published_item, 'category', 'unknown')
                        children = getattr(published_item, 'children', [])
                    except Exception:
                        # Use fallback values if we can't get the item
                        display_name = 'Published Item'
                        category = usage_key.block_type if hasattr(usage_key, 'block_type') else 'unknown'
                        children = []

                    published_items.append({
                        "type": category,
                        "id": str(usage_key),
                        "display_name": display_name
                    })

                    # If auto mode and this is a container, publish children
                    if publish_type == "auto" and category in ['sequential', 'chapter'] and children:
                        logger.info(f"Auto-publishing {len(children)} children of {category}")
                        children_published = []
                        for child_key in children:
                            try:
                                store.publish(child_key, acting_user.id)
                                logger.info(f"Published child: {child_key}")

                                # Try to get child details
                                try:
                                    child_item = store.get_item(child_key)
                                    child_display_name = getattr(child_item, 'display_name', 'Published Child')
                                    child_category = getattr(child_item, 'category', 'unknown')
                                except Exception:
                                    child_display_name = 'Published Child'
                                    child_category = (child_key.block_type
                                                      if hasattr(child_key, 'block_type')
                                                      else 'unknown')

                                children_published.append({
                                    "type": child_category,
                                    "id": str(child_key),
                                    "display_name": child_display_name
                                })
                            except Exception as child_error:
                                logger.warning(f"Failed to publish child {child_key}: {child_error}")

                        published_items.extend(children_published)

                except Exception as publish_error:
                    logger.error(f"Failed to publish {usage_key}: {publish_error}")

                    # If direct publish fails, it might be because the item doesn't exist
                    # or there's a permission issue
                    return {
                        "success": False,
                        "error": "publish_failed",
                        "message": (
                            f"Failed to publish content. This might be because the content doesn't exist "
                            f"in the draft store or has been deleted. Error: {publish_error}"
                        ),
                        "content_id": content_id,
                        "details": str(publish_error),
                        "suggestion": "Check if the content exists and try publishing parent container instead"
                    }

            except Exception as unit_error:
                logger.exception(f"Error in publish workflow: {unit_error}")
                return {
                    "success": False,
                    "error": "unit_publish_failed",
                    "message": f"Failed to publish unit: {unit_error}",
                    "content_id": content_id
                }

        return {
            "success": True,
            "content_id": content_id,
            "publish_type": publish_type,
            "published_items": published_items,
            "total_published": len(published_items),
            "message": f"Successfully published {len(published_items)} item(s)",
            "published_by": acting_user.username
        }

    except Exception as e:
        logger.exception(f"Error in publish_content_logic: {e}")
        return {
            "success": False,
            "error": "unexpected_error",
            "message": f"Unexpected error during publishing: {str(e)}",
            "content_id": content_id,
            "publish_type": publish_type
        }


def delete_xblock_logic(block_id, user_identifier=None):
    """
    Delete an xblock component from OpenEdX course structure using modulestore.

    Based on OpenEdX's official delete_item implementation in split.py.

    Args:
        block_id (str): Complete xblock usage key (e.g: block-v1:Org+Course+Run+type@html+block@id)
        user_identifier: User identifier (id, username, email) performing the deletion

    Returns:
        dict: Success/error response with details
    """
    import logging

    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import UsageKey
    from xmodule.modulestore.django import modulestore

    logger = logging.getLogger(__name__)
    User = get_user_model()

    # Get acting user using the helper function
    acting_user = _get_acting_user(user_identifier)
    if not acting_user:
        logger.error(f"No acting user found for identifier: {user_identifier}")
        return {
            "success": False,
            "error": "user_not_found",
            "message": f"No acting user available for identifier: {user_identifier}",
            "block_id": block_id
        }

    logger.info(f"delete_xblock_logic called with block_id={block_id}, user={acting_user.username}")

    # Parse usage key
    try:
        usage_key = UsageKey.from_string(block_id)
        course_key = usage_key.course_key
        logger.info(f"Deleting xblock: {usage_key} from course: {course_key}")
    except Exception as parse_error:
        logger.error(f"Failed to parse block_id '{block_id}': {parse_error}")
        return {
            "success": False,
            "error": "invalid_block_id",
            "message": f"Invalid block ID format: {parse_error}",
            "block_id": block_id
        }

    # Get modulestore and use the official delete_item method
    try:
        store = modulestore()

        # Check if xblock exists first
        try:
            xblock = store.get_item(usage_key)
            logger.info(f"Found xblock to delete: {xblock.display_name} ({xblock.category})")
        except Exception:
            return {
                "success": False,
                "error": "xblock_not_found",
                "message": f"XBlock not found: {block_id}",
                "block_id": block_id
            }

        # Use the official OpenEdX delete_item method
        # This handles all the complexity: parent updates, structure versioning, etc.
        result_course_key = store.delete_item(usage_key, acting_user.id)

        logger.info(f"Successfully deleted xblock: {usage_key}")
        logger.info(f"New course version: {result_course_key}")

        return {
            "success": True,
            "message": f"Successfully deleted xblock: {block_id}",
            "block_id": block_id,
            "block_type": xblock.category if hasattr(xblock, 'category') else 'unknown',
            "display_name": xblock.display_name if hasattr(xblock, 'display_name') else 'Unknown',
            "course_id": str(course_key),
            "new_course_version": str(result_course_key) if result_course_key else None
        }

    except ValueError as value_error:
        # This happens when trying to delete the course root or invalid operations
        logger.error(f"ValueError in delete_item: {value_error}")
        return {
            "success": False,
            "error": "invalid_operation",
            "message": f"Cannot delete xblock: {value_error}",
            "block_id": block_id
        }
    except Exception as delete_error:
        logger.exception(f"Error deleting xblock {usage_key}")
        return {
            "success": False,
            "error": "deletion_failed",
            "message": f"Failed to delete xblock: {delete_error}",
            "block_id": block_id,
            "user": acting_user.username
        }


def toggle_certificate_logic(course_id: str, certificate_id: str, is_active: bool, user_identifier=None):
    """
    Toggle certificate active status using OpenEdX CertificateManager pattern.

    Args:
        course_id: Course identifier (e.g., 'course-v1:Org+Course+Run')
        certificate_id: Certificate identifier to toggle
        is_active: Boolean to set certificate active status
        user_identifier: User performing the operation

    Returns:
        dict: Operation result with success status
    """
    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "toggle_certificate start course_id=%s certificate_id=%s is_active=%s requested_by=%s",
            course_id, certificate_id, is_active, str(user_identifier)
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {
                "success": False,
                "error": "user_not_found",
                "message": "Valid user required for certificate operations",
                "course_id": course_id
            }

        # Parse course key
        course_key = CourseKey.from_string(course_id)
        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}",
                "course_id": course_id
            }

        # Use OpenEdX CertificateManager pattern
        try:
            from cms.djangoapps.contentstore.views.certificates import CertificateManager

            # Get current certificates
            certificates = getattr(course, 'certificates', {})

            if 'certificates' not in certificates:
                certificates['certificates'] = []

            # Find the certificate to toggle
            certificate_found = False
            for certificate in certificates['certificates']:
                if str(certificate.get('id', '')) == str(certificate_id):
                    # Use official OpenEdX pattern: direct assignment
                    certificate['is_active'] = is_active
                    certificate_found = True
                    break

            if not certificate_found:
                return {
                    "success": False,
                    "error": "certificate_not_found",
                    "message": f"Certificate not found: {certificate_id}",
                    "course_id": course_id,
                    "certificate_id": certificate_id
                }

            # Update course with new certificate configuration
            course.certificates = certificates
            store.update_item(course, acting_user.id)

            action = "activated" if is_active else "deactivated"
            logger.info(f"Successfully {action} certificate {certificate_id} for course {course_id}")

            return {
                "success": True,
                "message": f"Certificate {action} successfully",
                "course_id": course_id,
                "certificate_id": certificate_id,
                "is_active": is_active,
                "action": action,
                "updated_by": acting_user.username
            }

        except ImportError:
            logger.warning("CertificateManager not available, using direct approach")
            # Fallback approach without CertificateManager
            certificates = getattr(course, 'certificates', {})

            if 'certificates' not in certificates:
                certificates['certificates'] = []

            # Find and update certificate
            for certificate in certificates['certificates']:
                if str(certificate.get('id', '')) == str(certificate_id):
                    certificate['is_active'] = is_active
                    break

            course.certificates = certificates
            store.update_item(course, acting_user.id)

            action = "activated" if is_active else "deactivated"
            return {
                "success": True,
                "message": f"Certificate {action} successfully (fallback method)",
                "course_id": course_id,
                "certificate_id": certificate_id,
                "is_active": is_active,
                "action": action
            }

    except Exception as e:
        logger.exception(f"Error toggling certificate: {e}")
        return {
            "success": False,
            "error": "toggle_failed",
            "message": f"Failed to toggle certificate: {str(e)}",
            "course_id": course_id,
            "certificate_id": certificate_id
        }


def toggle_certificate_simple_logic(course_id: str, is_active: bool, user_identifier=None):
    """
    Toggle certificate active status following official OpenedX pattern (without certificate_id).

    This follows the exact pattern from cms/djangoapps/contentstore/views/certificates.py
    certificate_activation_handler - activates/deactivates the first certificate found.

    Args:
        course_id: Course identifier (e.g., 'course-v1:Org+Course+Run')
        is_active: Boolean to set certificate active status
        user_identifier: User performing the operation

    Returns:
        dict: Operation result with success status
    """
    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "toggle_certificate_simple start course_id=%s is_active=%s requested_by=%s",
            course_id, is_active, str(user_identifier)
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {
                "success": False,
                "error": "user_not_found",
                "message": "Valid user required for certificate operations",
                "course_id": course_id
            }

        # Parse course key
        course_key = CourseKey.from_string(course_id)
        store = modulestore()
        course = store.get_course(course_key)

        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}",
                "course_id": course_id
            }

        # Use OpenedX CertificateManager pattern - exactly like official code
        try:
            from cms.djangoapps.contentstore.views.certificates import CertificateManager

            # Get certificates using official CertificateManager
            certificates = CertificateManager.get_certificates(course)

            # Follow official OpenedX pattern: activate/deactivate first certificate
            certificate_found = False
            for certificate in certificates:
                certificate['is_active'] = is_active
                certificate_found = True
                break  # Only modify the first certificate, just like official code

            if not certificate_found:
                return {
                    "success": False,
                    "error": "no_certificates_found",
                    "message": f"No certificates found in course: {course_id}",
                    "course_id": course_id
                }

            # Update course with new certificate configuration
            store.update_item(course, acting_user.id)

            # Track event like official OpenedX code
            try:
                cert_event_type = 'activated' if is_active else 'deactivated'
                CertificateManager.track_event(cert_event_type, {
                    'course_id': str(course.id),
                })
            except Exception as track_error:
                logger.warning(f"Could not track certificate event: {track_error}")

            action = "activated" if is_active else "deactivated"
            logger.info(f"Successfully {action} first certificate for course {course_id}")

            return {
                "success": True,
                "message": f"Certificate {action} successfully",
                "course_id": course_id,
                "is_active": is_active,
                "action": action,
                "method": "official_openedx_pattern",
                "updated_by": acting_user.username
            }

        except ImportError:
            logger.warning("CertificateManager not available, using direct approach")
            # Fallback approach without CertificateManager
            certificates = getattr(course, 'certificates', {})

            if 'certificates' not in certificates:
                certificates['certificates'] = []

            if not certificates['certificates']:
                return {
                    "success": False,
                    "error": "no_certificates_found",
                    "message": f"No certificates found in course: {course_id}",
                    "course_id": course_id
                }

            # Activate/deactivate first certificate
            certificates['certificates'][0]['is_active'] = is_active

            course.certificates = certificates
            store.update_item(course, acting_user.id)

            action = "activated" if is_active else "deactivated"
            return {
                "success": True,
                "message": f"Certificate {action} successfully (fallback method)",
                "course_id": course_id,
                "is_active": is_active,
                "action": action,
                "method": "fallback_direct",
                "updated_by": acting_user.username
            }

    except Exception as e:
        logger.exception(f"Error toggling certificate: {e}")
        return {
            "success": False,
            "error": "toggle_failed",
            "message": f"Failed to toggle certificate: {str(e)}",
            "course_id": course_id
        }


def manage_course_staff_logic(course_id, user_identifier, action, role_type="staff", acting_user_identifier=None):
    """
    Add or remove users from course staff roles.

    Args:
        course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
        user_identifier (str): User to add/remove (username, email, or user_id)
        action (str): "add" or "remove"
        role_type (str): Type of role - "staff" or "course_creator"
        acting_user_identifier: User performing the action

    Returns:
        dict: Success/error response with details
    """
    from common.djangoapps.student.auth import CourseCreatorRole, OrgContentCreatorRole
    from common.djangoapps.student.roles import CourseStaffRole
    from opaque_keys.edx.keys import CourseKey

    try:
        # Validate inputs
        if not course_id:
            return {
                "success": False,
                "error": "missing_course_id",
                "message": "course_id is required"
            }

        if not user_identifier:
            return {
                "success": False,
                "error": "missing_user_identifier",
                "message": "user_identifier is required"
            }

        if action not in ["add", "remove"]:
            return {
                "success": False,
                "error": "invalid_action",
                "message": "action must be 'add' or 'remove'"
            }

        if role_type not in ["staff", "course_creator"]:
            return {
                "success": False,
                "error": "invalid_role_type",
                "message": "role_type must be 'staff' or 'course_creator'"
            }

        # Normalize course_id: handle URL encoding/decoding and ensure proper format
        import urllib.parse

        # First decode any URL encoding (e.g., %2B -> +)
        course_id = urllib.parse.unquote(course_id)

        # Then handle cases where spaces were incorrectly interpreted as +
        # If we detect spaces in course_id, convert them back to +
        if ' ' in course_id and '+' not in course_id:
            # This handles the case where + was interpreted as spaces
            parts = course_id.split(' ')
            if len(parts) >= 3 and parts[0].startswith('course-v1:'):
                course_id = '+'.join(parts)
                logger.info(f"Converted spaces to + in course_id: {course_id}")

        # Get acting user (who is performing the action)
        acting_user = _get_acting_user(acting_user_identifier)
        if not acting_user:
            return {
                "success": False,
                "error": "acting_user_not_found",
                "message": f"Acting user not found: {acting_user_identifier}"
            }

        # Resolve target user
        target_user = _resolve_user(user_identifier)
        if not target_user:
            return {
                "success": False,
                "error": "target_user_not_found",
                "message": f"Target user not found: {user_identifier}"
            }

        # Parse course key
        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_course_id",
                "message": f"Invalid course_id format: {str(e)}"
            }

        # Verify course exists
        from xmodule.modulestore.django import modulestore
        store = modulestore()
        course = store.get_course(course_key)
        if not course:
            return {
                "success": False,
                "error": "course_not_found",
                "message": f"Course not found: {course_id}"
            }

        # Get the appropriate role class
        role_classes = {
            "staff": CourseStaffRole,
        }

        # Handle course_creator role differently (global role)
        if role_type == "course_creator":
            # Extract org from course_key for OrgContentCreatorRole
            org = course_key.org

            if action == "add":
                # Add global course creator role
                CourseCreatorRole().add_users(target_user)
                # Also add org-specific role
                OrgContentCreatorRole(org=org).add_users(target_user)

                logger.info(
                    f"Added course creator role to user {target_user.username} "
                    f"(global and org={org}) by {acting_user.username}"
                )

                return {
                    "success": True,
                    "message": f"Successfully added course creator role to {target_user.username}",
                    "action": "add",
                    "role_type": "course_creator",
                    "target_user": {
                        "id": target_user.id,
                        "username": target_user.username,
                        "email": target_user.email
                    },
                    "course_id": course_id,
                    "org": org,
                    "acting_user": acting_user.username
                }
            else:  # remove
                # Remove global course creator role
                CourseCreatorRole().remove_users(target_user)
                # Also remove org-specific role
                OrgContentCreatorRole(org=org).remove_users(target_user)

                logger.info(
                    f"Removed course creator role from user {target_user.username} "
                    f"(global and org={org}) by {acting_user.username}"
                )

                return {
                    "success": True,
                    "message": f"Successfully removed course creator role from {target_user.username}",
                    "action": "remove",
                    "role_type": "course_creator",
                    "target_user": {
                        "id": target_user.id,
                        "username": target_user.username,
                        "email": target_user.email
                    },
                    "course_id": course_id,
                    "org": org,
                    "acting_user": acting_user.username
                }

        # Handle course-specific roles (staff only)
        role_class = role_classes[role_type]
        role_instance = role_class(course_key)

        # Check if user already has the role
        has_role = role_instance.has_user(target_user)

        if action == "add":
            if has_role:
                return {
                    "success": False,
                    "error": "user_already_has_role",
                    "message": f"User {target_user.username} already has {role_type} role in course {course_id}"
                }

            # Add the role
            role_instance.add_users(target_user)

            logger.info(
                f"Added {role_type} role to user {target_user.username} "
                f"in course {course_id} by {acting_user.username}"
            )

            return {
                "success": True,
                "message": f"Successfully added {role_type} role to {target_user.username}",
                "action": "add",
                "role_type": role_type,
                "target_user": {
                    "id": target_user.id,
                    "username": target_user.username,
                    "email": target_user.email
                },
                "course_id": course_id,
                "acting_user": acting_user.username
            }

        else:  # remove
            if not has_role:
                return {
                    "success": False,
                    "error": "user_does_not_have_role",
                    "message": f"User {target_user.username} does not have {role_type} role in course {course_id}"
                }

            # Remove the role
            role_instance.remove_users(target_user)

            logger.info(
                f"Removed {role_type} role from user {target_user.username} "
                f"in course {course_id} by {acting_user.username}"
            )

            return {
                "success": True,
                "message": f"Successfully removed {role_type} role from {target_user.username}",
                "action": "remove",
                "role_type": role_type,
                "target_user": {
                    "id": target_user.id,
                    "username": target_user.username,
                    "email": target_user.email
                },
                "course_id": course_id,
                "acting_user": acting_user.username
            }

    except Exception as e:
        logger.exception(f"Error managing course staff: {e}")
        return {
            "success": False,
            "error": "operation_failed",
            "message": f"Failed to {action} {role_type} role: {str(e)}",
            "course_id": course_id,
            "user_identifier": user_identifier,
            "action": action,
            "role_type": role_type
        }


def list_course_staff_logic(course_id, role_type=None, acting_user_identifier=None):
    """
    List users with course staff roles.

    Args:
        course_id (str): Course identifier (e.g., course-v1:ORG+NUM+RUN)
        role_type (str, optional): Filter by role type - "staff", "course_creator", or None for all
        acting_user_identifier: User performing the query

    Returns:
        dict: Success response with list of users and their roles
    """
    import logging

    from common.djangoapps.student.auth import CourseCreatorRole, OrgContentCreatorRole
    from common.djangoapps.student.roles import CourseStaffRole
    from django.contrib.auth import get_user_model
    from opaque_keys.edx.keys import CourseKey

    logger = logging.getLogger(__name__)

    try:
        # Validate inputs
        if not course_id:
            return {
                "success": False,
                "error": "missing_course_id",
                "message": "course_id is required"
            }

        if role_type and role_type not in ["staff", "course_creator"]:
            return {
                "success": False,
                "error": "invalid_role_type",
                "message": "role_type must be 'staff', 'course_creator', or None"
            }

        # Normalize course_id: handle URL encoding/decoding and ensure proper format
        import urllib.parse

        # First decode any URL encoding (e.g., %2B -> +)
        course_id = urllib.parse.unquote(course_id)

        # Then handle cases where spaces were incorrectly interpreted as +
        # If we detect spaces in course_id, convert them back to +
        if ' ' in course_id and '+' not in course_id:
            # This handles the case where + was interpreted as spaces
            parts = course_id.split(' ')
            if len(parts) >= 3 and parts[0].startswith('course-v1:'):
                course_id = '+'.join(parts)
                logger.info(f"Converted spaces to + in course_id: {course_id}")

        # Parse course key
        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            return {
                "success": False,
                "error": "invalid_course_id",
                "message": f"Invalid course_id format. Expected format: 'course-v1:ORG+COURSE+RUN'. "
                           f"Received: '{course_id}'. Error: {str(e)}. "
                           f"Note: The API automatically handles URL encoding/decoding."
            }

        User = get_user_model()
        users_data = []

        # Get course staff users
        if not role_type or role_type == "staff":
            staff_role = CourseStaffRole(course_key)
            staff_users = staff_role.users_with_role()

            for user in staff_users:
                users_data.append({
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": "staff",
                    "role_description": "Course staff (can edit course content)"
                })

        # Get course creator users
        if not role_type or role_type == "course_creator":
            # Global course creators
            global_creator_role = CourseCreatorRole()
            global_creators = global_creator_role.users_with_role()

            # Organization-specific course creators
            org = course_key.org
            org_creator_role = OrgContentCreatorRole(org)
            org_creators = org_creator_role.users_with_role()

            # Combine and deduplicate
            all_creators = set(global_creators) | set(org_creators)

            for user in all_creators:
                # Check if user already added as staff
                if not any(u["user_id"] == user.id for u in users_data):
                    users_data.append({
                        "user_id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": "course_creator",
                        "role_description": "Course creator (can create new courses)"
                    })

        # Sort by username for consistent results
        users_data.sort(key=lambda x: x["username"])

        return {
            "success": True,
            "course_id": course_id,
            "role_type_filter": role_type,
            "total_users": len(users_data),
            "users": users_data,
            "acting_user": acting_user_identifier
        }

    except Exception as e:
        return {
            "success": False,
            "error": "query_failed",
            "message": f"Failed to list course staff: {str(e)}",
            "course_id": course_id,
            "role_type": role_type
        }


def add_ora_content_logic(vertical_id: str, ora_config: dict, user_identifier=None) -> dict:
    """
    Add Open Response Assessment (ORA) content component to a vertical in OpenEdX.

    ORAs support peer assessment, self assessment, and staff assessment workflows.

    Args:
        vertical_id (str): The vertical/unit ID where the ORA will be added
        ora_config (dict): Configuration for the ORA component with:

            * display_name (str): Name/title for the ORA
            * prompt (str): Question/prompt text for students
            * rubric (dict): Assessment rubric configuration
            * assessments (list): List of assessment types (self, peer, staff)
            * submission_start (str, optional): When submissions can start (ISO datetime)
            * submission_due (str, optional): When submissions are due (ISO datetime)
            * file_upload_type (str, optional): 'image', 'pdf-and-image', or None
            * allow_file_upload (bool, optional): Whether to allow file uploads
            * allow_text_response (bool, optional): Whether to allow text responses
            * leaderboard_show (int, optional): Number of top submissions to show

        user_identifier: User creating the ORA

    Returns:
        dict: Success/error response with ORA component details

    Example ora_config::

        {
            "display_name": "Essay Assignment",
            "prompt": "Write a 500-word essay on...",
            "rubric": {
                "criteria": [
                    {
                        "name": "Content",
                        "prompt": "How well does the essay address the topic?",
                        "options": [
                            {"name": "Excellent", "points": 4, "explanation": "Thoroughly addresses topic"},
                            {"name": "Good", "points": 3, "explanation": "Addresses topic well"},
                            {"name": "Fair", "points": 2, "explanation": "Partially addresses topic"},
                            {"name": "Poor", "points": 1, "explanation": "Does not address topic"}
                        ]
                    }
                ]
            },
            "assessments": [
                {"name": "self", "start": null, "due": null, "must_grade": 1, "must_be_graded_by": 1},
                {"name": "peer", "start": null, "due": null, "must_grade": 3, "must_be_graded_by": 2}
            ],
            "submission_start": "2024-01-01T00:00:00Z",
            "submission_due": "2024-12-31T23:59:59Z",
            "allow_text_response": true,
            "allow_file_upload": false,
            "file_upload_type": null,
            "leaderboard_show": 0
        }
    """

    from cms.djangoapps.contentstore.xblock_storage_handlers.create_xblock import create_xblock
    from django.contrib.auth import get_user_model
    from xmodule.modulestore.django import modulestore

    try:
        logger.info(
            "add_ora_content start vertical_id=%s requested_by=%s config_keys=%s",
            vertical_id, str(user_identifier), list((ora_config or {}).keys())
        )

        User = get_user_model()
        acting_user = _get_acting_user(user_identifier)

        if not acting_user:
            return {"success": False, "error": "No acting user available"}

        store, parent_item, usage_key_str, err = _validate_vertical_id(vertical_id)
        if err:
            return err

        # Validate and set defaults for ORA configuration
        if not ora_config:
            ora_config = {}

        display_name = ora_config.get('display_name', 'Open Response Assessment')
        prompt = ora_config.get('prompt', 'Enter your response here.')

        # Create the ORA XBlock
        component = create_xblock(
            parent_locator=str(parent_item.location),
            user=acting_user,
            category='openassessment',  # ORA XBlock category
            display_name=display_name
        )

        # Configure ORA-specific settings
        # Basic prompt configuration
        component.prompt = prompt

        # Configure submission settings
        submission_start = ora_config.get('submission_start')
        submission_due = ora_config.get('submission_due')

        if submission_start:
            component.submission_start = _parse_datetime_for_ora(submission_start)
        if submission_due:
            component.submission_due = _parse_datetime_for_ora(submission_due)

        # Configure response types
        component.allow_text_response = ora_config.get('allow_text_response', True)
        component.allow_file_upload = ora_config.get('allow_file_upload', False)

        if component.allow_file_upload:
            file_upload_type = ora_config.get('file_upload_type', 'pdf-and-image')
            component.file_upload_type = file_upload_type

        # Configure leaderboard
        component.leaderboard_show = ora_config.get('leaderboard_show', 0)

        # Configure rubric if provided
        rubric_config = ora_config.get('rubric')
        if rubric_config:
            component.rubric_criteria = _build_ora_rubric(rubric_config)

        # Configure assessments workflow
        assessments_config = ora_config.get('assessments', [])
        if assessments_config:
            component.rubric_assessments = _build_ora_assessments(assessments_config)
        else:
            # Default to self-assessment only
            component.rubric_assessments = [
                {
                    "name": "self-assessment",
                    "start": None,
                    "due": None,
                    "must_grade": 1,
                    "must_be_graded_by": 1
                }
            ]

        # Update the component in modulestore
        store.update_item(component, acting_user.id)

        logger.info(f"Successfully created ORA component: {component.location}")

        return {
            "success": True,
            "component_id": str(component.location),
            "parent_vertical": usage_key_str,
            "display_name": display_name,
            "prompt": prompt,
            "assessment_types": [step["name"] for step in component.rubric_assessments],
            "message": "ORA component created successfully"
        }

    except Exception as e:
        logger.exception(f"Error creating ORA content: {e}")
        return {
            "success": False,
            "error": str(e),
            "vertical_id": vertical_id,
            "requested_by": str(user_identifier)
        }


def _parse_datetime_for_ora(date_str):
    """Parse datetime string for ORA components"""
    if not date_str:
        return None

    try:
        from datetime import datetime

        # Validate that the string is a valid datetime and return it as string
        if date_str.endswith('Z'):
            # Normalize Z to +00:00 for validation
            normalized_date = date_str[:-1] + '+00:00'
            # Validate by parsing
            datetime.fromisoformat(normalized_date)
            # Return original format that OpenedX expects
            return date_str
        else:
            # Validate by parsing
            datetime.fromisoformat(date_str)
            # Return as-is if valid
            return date_str
    except ValueError as e:
        logger.warning(f"Invalid datetime format for ORA: {date_str}, error: {e}")
        return None


def _build_ora_rubric(rubric_config):
    """
    Build rubric criteria for ORA from configuration.

    Args:
        rubric_config (dict): Rubric configuration with criteria

    Returns:
        list: Formatted rubric criteria for ORA
    """
    criteria = []

    for criterion in rubric_config.get('criteria', []):
        criterion_data = {
            "name": criterion.get('name', 'Criterion'),
            "prompt": criterion.get('prompt', 'Evaluate this criterion'),
            "options": []
        }

        for option in criterion.get('options', []):
            option_data = {
                "name": option.get('name', 'Option'),
                "points": option.get('points', 1),
                "explanation": option.get('explanation', '')
            }
            criterion_data["options"].append(option_data)

        criteria.append(criterion_data)

    return criteria


def _build_ora_assessments(assessments_config):
    """
    Build assessment steps configuration for ORA.

    Args:
        assessments_config (list): List of assessment configurations

    Returns:
        list: Formatted assessment steps for ORA rubric_assessments field
    """
    assessment_steps = []

    for assessment in assessments_config:
        # Map short names to full ORA assessment names
        assessment_name = assessment.get('name', 'self')
        if assessment_name == 'self':
            assessment_name = 'self-assessment'
        elif assessment_name == 'peer':
            assessment_name = 'peer-assessment'
        elif assessment_name == 'staff':
            assessment_name = 'staff-assessment'
        elif assessment_name == 'student-training':
            assessment_name = 'student-training'

        assessment_data = {
            "name": assessment_name,
            "start": _parse_datetime_for_ora(assessment.get('start')),
            "due": _parse_datetime_for_ora(assessment.get('due')),
            "must_grade": assessment.get('must_grade', 1),
            "must_be_graded_by": assessment.get('must_be_graded_by', 1)
        }

        # Add specific configurations for different assessment types
        if assessment_name == "peer-assessment":
            assessment_data["must_grade"] = assessment.get('must_grade', 3)
            assessment_data["must_be_graded_by"] = assessment.get('must_be_graded_by', 2)
        elif assessment_name == "staff-assessment":
            assessment_data["required"] = assessment.get('required', False)

        assessment_steps.append(assessment_data)

    return assessment_steps


def get_submission_uuid_for_student(ora_location: str, student_username: str) -> str:
    """
    Get the submission UUID for a specific student and ORA.

    Args:
        ora_location (str): ORA XBlock location/usage key
        student_username (str): Username of the student

    Returns:
        str: submission_uuid or None if not found
    """
    try:
        from django.contrib.auth import get_user_model
        from opaque_keys.edx.keys import UsageKey
        from submissions import api as submissions_api

        User = get_user_model()

        # Get the user object
        try:
            student_user = User.objects.get(username=student_username)
            logger.info(
                f"Found student user: {student_user.username} (ID: {student_user.id})"
            )
        except User.DoesNotExist:
            logger.error(f"Student user '{student_username}' not found")
            return None

        # Clean and parse the ORA location key
        from urllib.parse import unquote
        cleaned_location = unquote(ora_location)
        cleaned_location = cleaned_location.replace(' ', '+')
        ora_usage_key = UsageKey.from_string(cleaned_location)

        # Try to get the submission for this specific student using OpenedX API
        try:
            # Try direct database query first (most reliable method)
            from submissions.models import StudentItem, Submission

            logger.info(
                f"Looking for submissions for student '{student_username}' (ID: {student_user.id}) "
                f"in ORA '{ora_location}'"
            )

            # First, get the StudentItem for this student and ORA
            try:
                student_item = StudentItem.objects.get(
                    student_id=str(student_user.id),
                    course_id=str(ora_usage_key.course_key),
                    item_id=str(ora_usage_key),
                    item_type='openassessment'
                )
                logger.info(f"Found StudentItem for student '{student_username}'")

                # Now get submissions for this student item
                submissions = Submission.objects.filter(student_item=student_item).order_by('-created_at')

                if submissions.exists():
                    submission = submissions.first()
                    logger.info(
                        f"Found submission for student '{student_username}': {submission.uuid}"
                    )
                    return submission.uuid
                else:
                    logger.warning(
                        f"No submissions found for StudentItem for student '{student_username}'"
                    )

            except StudentItem.DoesNotExist:
                logger.warning(
                    f"No StudentItem found for student '{student_username}' in ORA '{ora_location}'. "
                    f"This likely means the student has not submitted a response to this ORA yet."
                )

        except Exception as e:
            logger.error(
                f"Error with database query for student '{student_username}': {e}"
            )

            # Try alternative method - use submissions API
            try:
                logger.info(
                    "Trying alternative method - submissions API"
                )

                # Use get_submissions API method with correct parameters
                # The OpenEdX submissions API get_submissions method signature:
                # get_submissions(course_id, item_id, item_type, limit=None)
                try:
                    course_id = str(ora_usage_key.course_key)
                    item_id = str(ora_usage_key)
                    
                    submissions_list = submissions_api.get_submissions(
                        course_id=course_id,
                        item_id=item_id,
                        item_type='openassessment'
                    )

                    logger.info(
                        f"Found {len(submissions_list)} total submissions for ORA via API"
                    )

                    # Filter by student ID
                    for submission in submissions_list:
                        logger.debug(
                            f"Checking submission: student_id={submission.get('student_id')}, "
                            f"target={str(student_user.id)}"
                        )
                        if submission.get('student_id') == str(student_user.id):
                            logger.info(
                                f"Found submission via API filtering for student '{student_username}': {submission.get('uuid')}"
                            )
                            return submission.get('uuid')

                    logger.warning(
                        f"No submission found in API results for student '{student_username}' "
                        f"among {len(submissions_list)} submissions"
                    )

                except Exception as api_error:
                    logger.error(f"Submissions API call failed: {api_error}")

            except Exception as fallback_error:
                logger.error(
                    f"Fallback API method also failed for student '{student_username}': {fallback_error}"
                )

        logger.warning(
            f"No submission found for student '{student_username}' in ORA '{ora_location}' after trying all methods"
        )
        logger.info(
            "This likely means the student has not submitted a response to this ORA yet"
        )
        return None

    except Exception as e:
        logger.error(
            f"Error getting submission UUID for student '{student_username}': {e}"
        )
        return None


def list_ora_submissions_logic(ora_location: str, user_identifier=None) -> dict:
    """
    List all submissions for a specific ORA to help identify which students have submitted responses.

    Args:
        ora_location (str): ORA XBlock location/usage key
        user_identifier: User requesting the information

    Returns:
        dict: List of submissions with student information
    """
    try:
        from urllib.parse import unquote

        from django.contrib.auth import get_user_model
        from opaque_keys.edx.keys import UsageKey
        from submissions import api as submissions_api

        acting_user = _get_acting_user(user_identifier)
        logger.info(
            f"list_ora_submissions_logic: User {acting_user.username} requesting submissions for {ora_location}"
        )

        # Clean and parse the ORA location key
        cleaned_location = unquote(ora_location)
        cleaned_location = cleaned_location.replace(' ', '+')
        ora_usage_key = UsageKey.from_string(cleaned_location)

        submissions_list = []

        # Try to get all submissions for this ORA
        try:
            from submissions.models import StudentItem, Submission

            # Get all student items for this ORA (item_id and course_id)
            student_items = StudentItem.objects.filter(
                course_id=str(ora_usage_key.course_key),
                item_id=str(ora_usage_key),
                item_type='openassessment'
            )

            logger.info(
                f"Found {student_items.count()} student items for ORA"
            )

            # Get submissions for these student items
            submissions = Submission.objects.filter(
                student_item__in=student_items
            ).order_by('-created_at')

            logger.info(
                f"Found {submissions.count()} submissions for ORA"
            )

            # Process each submission and collect student information
            for submission in submissions:
                submissions_list.append({
                    'submission_uuid': submission.uuid,
                    'student_id': acting_user.id,
                    'student_username': acting_user.username,
                    'student_email': acting_user.email,
                    'submitted_at': submission.created_at.isoformat(),
                    'status': submission.status
                })

        except Exception as e:
            logger.error(
                f"Error getting submissions for ORA: {e}"
            )
            return {
                'success': False,
                'error': f'Error retrieving submissions: {str(e)}',
                'error_code': 'submissions_retrieval_error'
            }

        return {
            'success': True,
            'ora_location': ora_location,
            'total_submissions': len(submissions_list),
            'submissions': submissions_list,
            'message': f'Found {len(submissions_list)} submissions for this ORA'
        }

    except Exception as e:
        logger.error(
            f"Error in list_ora_submissions_logic: {e}"
        )
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_code': 'unexpected_error'
        }


def grade_ora_content_logic(
    ora_location: str,
    student_username: str = None,
    submission_uuid: str = None,
    grade_data: dict = None,
    user_identifier=None
) -> dict:
    """
    Grade an ORA submission using OpenedX staff grading functionality.

    Args:
        ora_location (str): ORA XBlock location/usage key
        student_username (str): Username of the student (alternative to submission_uuid)
        submission_uuid (str): UUID of the submission to grade (alternative to student_username)
        grade_data (dict): Grading data containing:
            - options_selected (dict): Selected rubric options for each criterion
            - criterion_feedback (dict): Optional feedback for each criterion
            - overall_feedback (str): Optional overall feedback for the submission
            - assess_type (str): 'full-grade' or 'regrade' (default: 'full-grade')
        user_identifier: User performing the grading

    Note:
        Either student_username OR submission_uuid must be provided, not both.

    Returns:
        dict: Result of the grading operation
    """
    try:
        acting_user = _get_acting_user(user_identifier)

        # Validate that we have either student_username or submission_uuid
        if not student_username and not submission_uuid:
            return {
                'success': False,
                'error': 'Either student_username or submission_uuid must be provided',
                'error_code': 'missing_identifier'
            }

        if student_username and submission_uuid:
            return {
                'success': False,
                'error': 'Cannot provide both student_username and submission_uuid',
                'error_code': 'conflicting_identifiers'
            }

        # If we have student_username, convert it to submission_uuid
        if student_username:
            logger.info(f"grade_ora_content_logic: User {acting_user.username} grading student '{student_username}'")
            submission_uuid = get_submission_uuid_for_student(ora_location, student_username)
            if not submission_uuid:
                return {
                    'success': False,
                    'error': f'No submission found for student "{student_username}" in this ORA',
                    'error_code': 'submission_not_found'
                }
            logger.info(f"Found submission UUID: {submission_uuid}")
        else:
            logger.info(f"grade_ora_content_logic: User {acting_user.username} grading submission {submission_uuid}")

        # Ensure grade_data is not None
        if grade_data is None:
            grade_data = {}

        # Import OpenedX modules lazily to avoid initialization issues
        from urllib.parse import unquote

        from opaque_keys.edx.keys import UsageKey
        from openassessment.assessment.api import staff as staff_api
        from openassessment.workflow import api as workflow_api
        from submissions import api as submissions_api
        from xmodule.modulestore.django import modulestore

        # Clean and parse the ORA location key
        # Handle URL encoding and spaces that might appear in the key
        try:
            # First try URL decoding
            cleaned_location = unquote(ora_location)
            # Replace any remaining spaces with + signs (common in OpenedX keys)
            cleaned_location = cleaned_location.replace(' ', '+')
            logger.info(f"Cleaned ORA location: '{ora_location}' -> '{cleaned_location}'")

            ora_usage_key = UsageKey.from_string(cleaned_location)
        except Exception as e:
            logger.error(f"Invalid ORA location key '{ora_location}' (cleaned: '{cleaned_location}'): {e}")
            return {
                'success': False,
                'error': f'Invalid ORA location: {str(e)}',
                'error_code': 'invalid_ora_location'
            }

        # Get the ORA XBlock to access configuration
        store = modulestore()
        try:
            ora_xblock = store.get_item(ora_usage_key)
        except Exception as e:
            logger.error(f"ORA XBlock not found for location '{ora_location}': {e}")
            return {
                'success': False,
                'error': f'ORA not found: {str(e)}',
                'error_code': 'ora_not_found'
            }

        # Verify this is actually an ORA XBlock
        if getattr(ora_xblock, 'category', None) != 'openassessment':
            return {
                'success': False,
                'error': f'XBlock at {ora_location} is not an ORA component',
                'error_code': 'not_ora_xblock'
            }

        # Validate submission exists
        try:
            submission = submissions_api.get_submission(submission_uuid)
            if not submission:
                return {
                    'success': False,
                    'error': f'Submission {submission_uuid} not found',
                    'error_code': 'submission_not_found'
                }
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_uuid}: {e}")
            return {
                'success': False,
                'error': f'Error retrieving submission: {str(e)}',
                'error_code': 'submission_retrieval_error'
            }

        # Extract grading data with defaults
        options_selected = grade_data.get('options_selected', {})
        criterion_feedback = grade_data.get('criterion_feedback', {})
        overall_feedback = grade_data.get('overall_feedback', '')
        assess_type = grade_data.get('assess_type', 'full-grade')

        # Validate required grading data
        if not options_selected:
            return {
                'success': False,
                'error': 'options_selected is required for grading',
                'error_code': 'missing_options_selected'
            }

        # Get course and item IDs for staff grading workflow
        course_id = str(ora_usage_key.course_key)
        item_id = str(ora_usage_key)

        # Create the staff assessment
        try:
            # Get rubric configuration from the ORA XBlock
            # Try different attributes to find the actual rubric criteria
            rubric_data = None
            rubric_criteria = []

            # Try various ORA XBlock attributes for rubric data
            possible_rubric_attrs = ['rubric', 'rubric_criteria', 'prompts', 'rubric_assessments']

            for attr_name in possible_rubric_attrs:
                attr_value = getattr(ora_xblock, attr_name, None)
                logger.info(f"Checking attribute '{attr_name}': {type(attr_value)} = {attr_value}")

                if attr_value:
                    if attr_name == 'rubric' and isinstance(attr_value, dict):
                        # This should be the main rubric with criteria
                        rubric_criteria = attr_value.get('criteria', [])
                        logger.info(f"Found rubric criteria in 'rubric' attribute: {rubric_criteria}")
                        break
                    elif attr_name == 'rubric_criteria':
                        rubric_criteria = attr_value if isinstance(attr_value, list) else []
                        logger.info(f"Found rubric criteria in 'rubric_criteria' attribute: {rubric_criteria}")
                        break

            # If we still don't have criteria, try to access the rubric field more directly
            if not rubric_criteria:
                logger.info("Trying direct access to ORA rubric fields...")

                # Try to access the rubric field which should contain the actual criteria
                if hasattr(ora_xblock, 'fields') and 'rubric' in ora_xblock.fields:
                    rubric_field = ora_xblock.fields['rubric']
                    logger.info(f"Found rubric field: {rubric_field}")
                    if hasattr(rubric_field, 'default') and isinstance(rubric_field.default, dict):
                        rubric_criteria = rubric_field.default.get('criteria', [])

                # Alternative: try to get the definition data
                if not rubric_criteria and hasattr(ora_xblock, 'definition_data'):
                    definition = ora_xblock.definition_data
                    logger.info(f"Checking definition_data: {definition}")
                    if isinstance(definition, dict) and 'rubric' in definition:
                        rubric_criteria = definition['rubric'].get('criteria', [])

            logger.info(f"Creating staff assessment for submission {submission_uuid}")
            logger.info(f"Final extracted rubric criteria: {rubric_criteria}")
            logger.info(
                f"Expected rubric criteria names: "
                f"{[criterion.get('name') for criterion in rubric_criteria if isinstance(criterion, dict)]}"
            )
            logger.info(f"Received options_selected: {options_selected}")

            # Validate that the criterion names in options_selected match the rubric
            rubric_criteria_names = {
                criterion.get('name') for criterion in rubric_criteria
                if isinstance(criterion, dict) and 'name' in criterion
            }
            provided_criteria_names = set(options_selected.keys())

            if not rubric_criteria_names:
                logger.warning("No rubric criteria found - proceeding without validation")
                # If we can't find rubric criteria, proceed anyway (might be a different ORA setup)
            elif not provided_criteria_names.issubset(rubric_criteria_names):
                missing_criteria = rubric_criteria_names - provided_criteria_names
                invalid_criteria = provided_criteria_names - rubric_criteria_names
                error_msg = (
                    f"Criterion name mismatch. Expected: {list(rubric_criteria_names)}, "
                    f"Got: {list(provided_criteria_names)}"
                )
                if missing_criteria:
                    error_msg += f". Missing: {list(missing_criteria)}"
                if invalid_criteria:
                    error_msg += f". Invalid: {list(invalid_criteria)}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': 'criterion_name_mismatch',
                    'expected_criteria': list(rubric_criteria_names),
                    'provided_criteria': list(provided_criteria_names),
                    'debug_info': {
                        'rubric_data_found': rubric_criteria,
                        'ora_attributes': {
                            attr: getattr(ora_xblock, attr, 'NOT_FOUND')
                            for attr in possible_rubric_attrs
                        }
                    }
                }

            # Create the assessment using OpenedX staff API
            assessment_data = {
                'submission_uuid': submission_uuid,
                'options_selected': options_selected,
                'criterion_feedback': criterion_feedback,
                'overall_feedback': overall_feedback,
                'assess_type': assess_type
            }

            logger.info(f"Creating staff assessment with data: {assessment_data}")

            # Prepare rubric_dict for the staff API
            # Convert our rubric_criteria list to the expected format
            rubric_dict = {
                'criteria': rubric_criteria
            }

            logger.info(f"Using rubric_dict: {rubric_dict}")

            # Use the staff API to create the assessment
            # The staff_api.create_assessment expects: (submission_uuid, user_id,
            # options_selected, criterion_feedback, overall_feedback, rubric_dict)
            try:
                assessment = staff_api.create_assessment(
                    submission_uuid,
                    user_identifier,  # Staff user ID
                    options_selected,  # Dict of criterion_name -> option_name
                    criterion_feedback,  # Dict of criterion_name -> feedback text
                    overall_feedback,  # String with overall feedback
                    rubric_dict  # Dict containing the rubric criteria
                )
                logger.info(f"Staff assessment created successfully: {assessment}")
            except Exception as staff_api_error:
                logger.error(f"Error with staff_api.create_assessment: {staff_api_error}")

                # Try alternative parameter order
                try:
                    assessment = staff_api.create_assessment(
                        submission_uuid,
                        user_identifier,
                        options_selected,
                        rubric_dict,  # Try rubric_dict before feedback
                        criterion_feedback,
                        overall_feedback
                    )
                    logger.info(f"Staff assessment created with alternative parameter order: {assessment}")
                except Exception as alt_error:
                    logger.error(f"Alternative parameter order failed: {alt_error}")
                    raise staff_api_error  # Re-raise the original error

            # Update the workflow to complete the assessment
            from openassessment.workflow import api as workflow_api

            logger.info(f"Attempting to update workflow for submission {submission_uuid}")

            try:
                # Get the workflow for this submission
                workflow = workflow_api.get_workflow_for_submission(
                    submission_uuid
                )

                if workflow:
                    logger.info(f"Found workflow for submission: {workflow}")

                    # Update workflow to mark staff assessment as complete
                    # Try different methods to update the workflow
                    try:
                        workflow_api.update_from_assessments(
                            submission_uuid,
                            course_id,
                            item_id
                        )
                        logger.info(f"Workflow updated successfully for submission {submission_uuid}")
                    except Exception as workflow_update_error:
                        logger.warning(
                            f"Could not update workflow with update_from_assessments: "
                            f"{workflow_update_error}"
                        )

                        # Try alternative method
                        try:
                            workflow_api.update_from_assessments(submission_uuid)
                            logger.info(f"Workflow updated with alternative method")
                        except Exception as alt_workflow_error:
                            logger.warning(f"Alternative workflow update also failed: {alt_workflow_error}")
                            # Don't fail the whole operation if workflow update fails
                            pass
                else:
                    logger.warning(f"No workflow found for submission {submission_uuid}")
            except Exception as workflow_error:
                logger.warning(f"Error working with workflow: {workflow_error}")
                # Don't fail the whole operation if workflow operations fail
                pass

            return {
                'success': True,
                'message': 'ORA grading completed successfully',
                'assessment_id': assessment.get('id') if isinstance(assessment, dict) else None,
                'submission_uuid': submission_uuid,
                'ora_location': ora_location,
                'grade_data': assessment_data,
                'points_earned': assessment.get('points_earned') if isinstance(assessment, dict) else None,
                'points_possible': assessment.get('points_possible') if isinstance(assessment, dict) else None
            }

        except Exception as e:
            logger.error(f"Error creating staff assessment for submission {submission_uuid}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Error creating staff assessment: {str(e)}',
                'error_code': 'assessment_creation_error',
                'submission_uuid': submission_uuid,
                'ora_location': ora_location
            }

    except Exception as e:
        logger.error(f"Unexpected error in grade_ora_content_logic: {e}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_code': 'unexpected_error'
        }

def get_ora_details_logic(ora_location: str, user_identifier=None) -> dict:
    """
    Get detailed information about an ORA component including rubric and submission details.

    Args:
        ora_location (str): ORA XBlock location/usage key
        user_identifier: User requesting the information

    Returns:
        dict: Detailed ORA information including rubric structure
    """
    try:
        acting_user = _get_acting_user(user_identifier)
        logger.info(
            "get_ora_details_logic: user=%s ora_location=%s",
            getattr(acting_user, 'username', None),
            ora_location,
        )

        # Import OpenedX modules lazily to avoid initialization issues
        from urllib.parse import unquote

        from opaque_keys.edx.keys import UsageKey
        from xmodule.modulestore.django import modulestore

        # Helpers
        def _parse_usage_key(raw: str):
            # Handle URL parameter parsing: + signs become spaces in URL parameters
            # We need to convert them back to + for OpenedX UsageKey format
            cleaned = unquote(raw)  # First decode any URL encoding (%2B -> +)
            cleaned = cleaned.replace(' ', '+')  # Convert spaces back to + (from URL parameter parsing)
            logger.info("Cleaned ORA location: '%s' -> '%s'", raw, cleaned)

            # Validate it looks like a proper UsageKey format
            if not cleaned.startswith('block-v1:') or '+type@' not in cleaned:
                raise ValueError(
                    f"Invalid UsageKey format. "
                    f"Expected: block-v1:ORG+COURSE+RUN+type@openassessment+block@ID "
                    f"Received: {cleaned}"
                )

            key = UsageKey.from_string(cleaned)
            # Guard against BlockKey (missing course context)
            if not hasattr(key, 'course_key'):
                raise ValueError(
                    "Received a BlockKey without course context. "
                    f"Expected: block-v1:ORG+COURSE+RUN+type@openassessment+block@ID "
                    f"Received: {cleaned}"
                )
            return key

        def _extract_rubric_criteria(xblock) -> list:
            """Return a list of rubric criteria dicts if available; [] otherwise."""
            # Preferred attributes
            for attr in ('rubric_criteria', 'rubric_criteria_with_labels'):
                data = getattr(xblock, attr, None)
                if data:
                    return data if isinstance(data, list) else data.get('criteria', [])

            # Method-based accessor
            get_rubric = getattr(xblock, 'get_rubric', None)
            if callable(get_rubric):
                try:
                    rubric_dict = get_rubric()
                    if isinstance(rubric_dict, dict):
                        crit = rubric_dict.get('criteria', [])
                        if crit:
                            return crit
                except Exception as err:
                    logger.info("get_rubric() failed: %s", err)

            # Fallback attributes
            data = getattr(xblock, 'rubric', None)
            if isinstance(data, dict):
                return data.get('criteria', [])
            if isinstance(data, list):
                return data

            # Last-ditch attempts on older fields
            if hasattr(xblock, 'criteria'):
                crit = getattr(xblock, 'criteria')
                if isinstance(crit, list) and crit:
                    return crit
            if hasattr(xblock, 'rubric_criteria_values'):
                crit = getattr(xblock, 'rubric_criteria_values')
                if isinstance(crit, list) and crit:
                    return crit
            return []

        # 1) Parse key safely
        try:
            ora_usage_key = _parse_usage_key(ora_location)
        except Exception as e:
            logger.error("Invalid ORA location key: %s", e)
            return {
                'success': False,
                'error': str(e),
                'error_code': 'invalid_ora_location',
                'provided': ora_location,
            }

        # 2) Load XBlock
        try:
            store = modulestore()
            ora_xblock = store.get_item(ora_usage_key)
        except Exception as e:
            logger.error("Could not load ORA XBlock for %s: %s", ora_usage_key, e)
            return {
                'success': False,
                'error': f'ORA component not found: {str(e)}',
                'error_code': 'ora_not_found',
                'ora_location': ora_location,
            }

        if not getattr(ora_xblock, 'category', None) == 'openassessment':
            return {
                'success': False,
                'error': f'XBlock at {ora_location} is not an ORA component',
                'error_code': 'not_ora_xblock',
            }

        # 3) Extract rubric
        rubric_criteria = _extract_rubric_criteria(ora_xblock)
        logger.info("Extracted rubric criteria count: %s", len(rubric_criteria or []))

        # Normalize criteria into a simple, consistent shape
        def _as_dict(criterion):
            if isinstance(criterion, dict):
                name = criterion.get('name')
                prompt = criterion.get('prompt')
                order_num = criterion.get('order_num')
                options = criterion.get('options', [])
            else:
                name = getattr(criterion, 'name', None)
                prompt = getattr(criterion, 'prompt', None)
                order_num = getattr(criterion, 'order_num', None)
                options = getattr(criterion, 'options', [])
            norm_opts = []
            for opt in options or []:
                if isinstance(opt, dict):
                    norm_opts.append({
                        'name': opt.get('name'),
                        'explanation': opt.get('explanation'),
                        'points': opt.get('points'),
                        'order_num': opt.get('order_num'),
                    })
                else:
                    norm_opts.append({
                        'name': getattr(opt, 'name', None),
                        'explanation': getattr(opt, 'explanation', None),
                        'points': getattr(opt, 'points', None),
                        'order_num': getattr(opt, 'order_num', None),
                    })
            return {
                'name': name,
                'prompt': prompt,
                'order_num': order_num,
                'options': norm_opts,
            }

        criteria_details = [_as_dict(c) for c in (rubric_criteria or [])]

        # 4) Build response
        ora_info = {
            'ora_location': ora_location,
            'display_name': getattr(ora_xblock, 'display_name', 'ORA Component'),
            'prompt': getattr(ora_xblock, 'prompt', ''),
            'submission_start': getattr(ora_xblock, 'submission_start', None),
            'submission_due': getattr(ora_xblock, 'submission_due', None),
            'allow_text_response': getattr(ora_xblock, 'allow_text_response', True),
            'allow_file_upload': getattr(ora_xblock, 'allow_file_upload', False),
            'file_upload_type': getattr(ora_xblock, 'file_upload_type', None),
            'assessment_steps': getattr(ora_xblock, 'assessment_steps', []),
            'rubric': {
                'criteria': criteria_details,
            },
        }

        example_options_selected = {}
        for c in criteria_details:
            if c.get('name') and c.get('options'):
                example_options_selected[c['name']] = c['options'][0]['name']

        return {
            'success': True,
            'ora_info': ora_info,
            'example_options_selected': example_options_selected,
            'criterion_names': [c.get('name') for c in criteria_details if c.get('name')],
            'message': f'Successfully retrieved ORA details for {ora_location}',
        }

    except Exception as e:
        logger.error("Unexpected error in get_ora_details_logic: %s", e)
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_code': 'unexpected_error',
        }
