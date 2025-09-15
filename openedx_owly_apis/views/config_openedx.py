from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# Logic operations for configuration endpoints
from openedx_owly_apis.operations.config import is_owly_chat_enabled_logic


class OpenedXConfigViewSet(viewsets.ViewSet):
    """
    ViewSet para configuracuión de la plataforma Open edX.
    """
    @action(detail=False, methods=['get'], url_path='enable_owly_chat')
    def enable_owly_chat(self, request):
        """Return whether the Owly chat is enabled by waffle flag.

        Endpoint behavior as requested in OWLY-170:
        - Queries a waffle flag (owly_chat.enable) to determine availability.
        - If enabled, returns {"enabled": true}; else returns {"enabled": false}.
        """
        result = is_owly_chat_enabled_logic(request)
        return Response(result)
