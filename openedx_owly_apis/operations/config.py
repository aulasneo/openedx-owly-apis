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


def is_owly_chat_enabled_logic(request, user_email=None) -> Dict[str, bool]:
    """Return whether the Owly chat feature is enabled via waffle flag.

    Uses waffle Flag.is_active_for_user to respect percentage, groups, and user context.
    Falls back to False on any error or when the flag is missing.

    Args:
        request: Django request object
        user_email (str, optional): Email of specific user to check. If provided,
                                   checks for that user instead of request.user
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

        # Determinar qué usuario verificar
        target_user = request.user
        if user_email:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                target_user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                return {
                    "enabled": False,
                    "error": "user_not_found",
                    "message": f"User with email {user_email} not found"
                }
            except Exception as e:
                logger.error(f"Error finding user {user_email}: {e}")
                return {
                    "enabled": False,
                    "error": "user_lookup_failed",
                    "message": f"Failed to lookup user: {str(e)}"
                }

        # Usar el método is_active_for_user del objeto flag
        enabled = bool(flag.is_active_for_user(target_user))

        return {"enabled": enabled}
    except Exception as e:
        # Conservative fallback: if waffle isn't available or any error occurs,
        # treat as disabled.
        logger.error(f"Error checking waffle flag: {e}")
        return {"enabled": False}
