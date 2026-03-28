import logging

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from openedx.core.lib.api.authentication import BearerAuthentication
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

# Logic operations for configuration endpoints
from openedx_owly_apis.operations.config import is_owly_chat_enabled_logic
from openedx_owly_apis.views.v1.response_utils import success_response

logger = logging.getLogger(__name__)


class OpenedXConfigViewSet(viewsets.ViewSet):
    """Configuration endpoints for the Open edX platform integration."""
    authentication_classes = (
        JwtAuthentication,
        BearerAuthentication,
        SessionAuthentication,
    )
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['get'],
        url_path='enable_owly_chat'
    )
    def enable_owly_chat(self, request):
        """Return whether the Owly chat is enabled by waffle flag.

        Endpoint behavior as requested in OWLY-170:
        - Queries a waffle flag (owly_chat.enable) to determine availability.
        - If enabled, returns {"enabled": true}; else returns {"enabled": false}.
        - Uses request.user for waffle flag evaluation.

        Examples:
        GET /api/v1/owly-config/enable_owly_chat/
        """
        result = is_owly_chat_enabled_logic(request)
        return success_response(result)
