# coding=utf-8
"""
Common Pluggable Django App settings.
"""


def plugin_settings(settings):
    """
    Inject local settings into django settings.
    """
    # settings.EXAMPLE = value
    del settings  # used for side-effect documentation; no-op to satisfy lint
