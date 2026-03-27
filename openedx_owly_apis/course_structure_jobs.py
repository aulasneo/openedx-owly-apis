"""Cache-backed job helpers for async course structure creation."""

from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone


JOB_CACHE_KEY_PREFIX = "openedx_owly_apis:course_structure_job"
JOB_CACHE_TIMEOUT_SECONDS = 60 * 60


def _job_cache_key(job_id):
    return f"{JOB_CACHE_KEY_PREFIX}:{job_id}"


def _timestamp():
    return timezone.now().isoformat()


def create_course_structure_job(course_id, edit=False, user_identifier=None):
    """Create a pending async job entry and return its payload."""
    job_id = str(uuid4())
    payload = {
        "job_id": job_id,
        "status": "pending",
        "course_id": course_id,
        "edit_mode": bool(edit),
        "requested_by": str(user_identifier) if user_identifier is not None else None,
        "created_at": _timestamp(),
        "updated_at": _timestamp(),
    }
    cache.set(_job_cache_key(job_id), payload, JOB_CACHE_TIMEOUT_SECONDS)
    return payload


def get_course_structure_job(job_id):
    """Return the cached async job payload, if present."""
    return cache.get(_job_cache_key(job_id))


def update_course_structure_job(job_id, **changes):
    """Update an existing async job payload and persist it back to cache."""
    payload = get_course_structure_job(job_id) or {"job_id": job_id}
    payload.update(changes)
    payload["updated_at"] = _timestamp()
    cache.set(_job_cache_key(job_id), payload, JOB_CACHE_TIMEOUT_SECONDS)
    return payload
