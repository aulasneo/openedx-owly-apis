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
