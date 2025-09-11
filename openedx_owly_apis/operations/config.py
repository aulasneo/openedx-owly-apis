"""
Operations for platform configuration queries.

Implements logic for checking feature toggles/waffle flags related to Owly.

Contract:
- Input: Django request (to evaluate user/context-sensitive waffle flags correctly).
- Output: dict {"enabled": bool}
"""
from __future__ import annotations

from typing import Dict

FLAG_NAME = "owly_chat.enable"


def is_owly_chat_enabled_logic(request) -> Dict[str, bool]:
    """Return whether the Owly chat feature is enabled via waffle flag.

    Uses waffle.flag_is_active to respect percentage, groups, and user context.
    Falls back to False on any error or when the flag is missing.
    """
    try:
        # waffle is available in edx-platform; this respects request/user context
        from waffle import flag_is_active  # type: ignore

        enabled = bool(flag_is_active(request, FLAG_NAME))
        return {"enabled": enabled}
    except Exception:
        # Conservative fallback: if waffle isn't available or any error occurs,
        # treat as disabled.
        return {"enabled": False}
