"""Celery tasks for openedx_owly_apis."""

from celery import shared_task  # pylint: disable=import-error

from openedx_owly_apis.course_structure_jobs import update_course_structure_job
from openedx_owly_apis.operations.courses import create_course_structure_logic, publish_content_logic
from openedx_owly_apis.publish_jobs import update_publish_content_job


@shared_task(name="openedx_owly_apis.create_course_structure")
def create_course_structure_task(job_id, course_id, units_config, edit=False, user_identifier=None):
    """Run course structure creation asynchronously and store progress in cache."""
    update_course_structure_job(
        job_id,
        status="running",
        progress_message="Creating course structure",
    )

    try:
        result = create_course_structure_logic(
            course_id=course_id,
            units_config=units_config,
            edit=edit,
            user_identifier=user_identifier,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
        result = {
            "success": False,
            "error": str(exc),
            "course_id": course_id,
            "requested_by": str(user_identifier),
        }

    if result.get("success"):
        return update_course_structure_job(
            job_id,
            status="success",
            progress_message="Course structure created",
            result=result,
            completed_at=result.get("completed_at"),
        )

    return update_course_structure_job(
        job_id,
        status="failed",
        progress_message="Course structure creation failed",
        result=result,
        error=result.get("error"),
        completed_at=result.get("completed_at"),
    )


@shared_task(name="openedx_owly_apis.publish_content")
def publish_content_task(job_id, content_id, publish_type="auto", user_identifier=None):
    """Run content publishing asynchronously and store progress in cache."""
    update_publish_content_job(
        job_id,
        status="running",
        progress_message="Publishing content",
    )

    try:
        result = publish_content_logic(
            content_id=content_id,
            publish_type=publish_type,
            user_identifier=user_identifier,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
        result = {
            "success": False,
            "error": str(exc),
            "content_id": content_id,
            "publish_type": publish_type,
            "requested_by": str(user_identifier),
        }

    if result.get("success"):
        return update_publish_content_job(
            job_id,
            status="success",
            progress_message="Content published",
            result=result,
            completed_at=result.get("completed_at"),
        )

    return update_publish_content_job(
        job_id,
        status="failed",
        progress_message="Content publishing failed",
        result=result,
        error=result.get("error"),
        completed_at=result.get("completed_at"),
    )
