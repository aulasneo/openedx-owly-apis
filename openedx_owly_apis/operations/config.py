"""
Operations for platform configuration queries.

Implements logic for checking feature toggles/waffle flags related to Owly.

Contract:
- Input: Django request (to evaluate user/context-sensitive waffle flags correctly).
- Output: dict {"enabled": bool}
"""
from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)
FLAG_NAME = "owly_chat.enable"


def is_owly_chat_enabled_logic(request) -> Dict[str, bool]:
    """Return whether the Owly chat feature is enabled via waffle flag.

    Uses waffle Flag.is_active_for_user to respect percentage, groups, and user context.
    Falls back to False on any error or when the flag is missing.

    Args:
        request: Django request object (uses request.user for waffle evaluation)
        session_tokens: Optional dict with sessionid and csrftoken for external use
    """
    try:
        # waffle is available in edx-platform; this respects request/user context
        from waffle.models import Flag

        # Verificar que el flag existe
        try:
            flag = Flag.objects.get(name=FLAG_NAME)
        except Flag.DoesNotExist:
            logger.error(f"Flag {FLAG_NAME} does not exist!")
            return {"enabled": False}

        # Usar request.user para la evaluación del waffle flag
        user = request.user

        # Verificar si el usuario está autenticado (no es AnonymousUser)
        if user:
            enabled = bool(flag.is_active_for_user(user))
            logger.info(f"Authenticated user {user.username} (ID: {user.id}) has flag {FLAG_NAME} enabled: {enabled}")
        else:
            enabled = bool(flag_is_active(request, FLAG_NAME))
            logger.info(f"Anonymous user has flag {FLAG_NAME} enabled: {enabled}")

        return {"enabled": enabled}

    except Exception as e:
        logger.error(f"Error evaluating waffle flag {FLAG_NAME}: {e}")
        return {"enabled": False}
