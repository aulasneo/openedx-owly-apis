"""Cache-backed job helpers for async content publishing."""

from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

JOB_CACHE_KEY_PREFIX = "openedx_owly_apis:publish_job"
JOB_CACHE_TIMEOUT_SECONDS = 60 * 60


def _job_cache_key(job_id):
    return "{}:{}".format(JOB_CACHE_KEY_PREFIX, job_id)


def _timestamp():
    return timezone.now().isoformat()


def create_publish_content_job(content_id, publish_type="auto", user_identifier=None, course_id=None):
    """Create a pending async publish job entry and return its payload."""
    job_id = str(uuid4())
    payload = {
        "job_id": job_id,
        "status": "pending",
        "content_id": content_id,
        "publish_type": publish_type,
        "course_id": course_id,
        "requested_by": str(user_identifier) if user_identifier is not None else None,
        "created_at": _timestamp(),
        "updated_at": _timestamp(),
    }
    cache.set(_job_cache_key(job_id), payload, JOB_CACHE_TIMEOUT_SECONDS)
    return payload


def get_publish_content_job(job_id):
    """Return the cached async publish job payload, if present."""
    return cache.get(_job_cache_key(job_id))


def update_publish_content_job(job_id, **changes):
    """Update an existing async publish job payload and persist it back to cache."""
    payload = get_publish_content_job(job_id) or {"job_id": job_id}
    payload.update(changes)
    payload["updated_at"] = _timestamp()
    cache.set(_job_cache_key(job_id), payload, JOB_CACHE_TIMEOUT_SECONDS)
    return payload
