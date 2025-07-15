"""
openedx_owly_apis Django application initialization.
"""

from django.apps import AppConfig


class OpenedxOwlyApisConfig(AppConfig):
    """
    Configuration for the openedx_owly_apis Django application.
    """

    name = 'openedx_owly_apis'

    plugin_app = {
        PluginURLs.CONFIG: {
            'cms.djangoapp': {
                PluginURLs.NAMESPACE: 'openedx_owly',
                PluginURLs.REGEX: r'^api/',
                PluginURLs.RELATIVE_PATH: 'urls',
            },
            'lms.djangoapp': {
                PluginURLs.NAMESPACE: 'openedx_owly',
                PluginURLs.REGEX: r'^api/',
                PluginURLs.RELATIVE_PATH: 'urls',
            },
        },
        PluginSettings.CONFIG: {
            'cms.djangoapp': {
                'common': {
                    PluginSettings.RELATIVE_PATH: 'settings.common',
                },
            },
            'lms.djangoapp': {
                'common': {
                    PluginSettings.RELATIVE_PATH: 'settings.common',
                },
            },
        },
    }
