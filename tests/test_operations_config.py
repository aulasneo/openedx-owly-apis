from types import SimpleNamespace

from openedx_owly_apis.operations import config as config_ops


class _Flag:
    def __init__(self, enabled):
        self._enabled = enabled

    def is_active_for_user(self, _user):
        return self._enabled


class _Manager:
    def __init__(self, flag):
        self._flag = flag

    def get(self, name):
        assert name == config_ops.FLAG_NAME
        return self._flag


class _MissingManager:
    def get(self, _name):
        raise _FlagModel.DoesNotExist


class _FlagModel:
    DoesNotExist = type("DoesNotExist", (Exception,), {})


def test_is_owly_chat_enabled_for_authenticated_user(monkeypatch):
    flag_model = type("Flag", (), {"objects": _Manager(_Flag(True)), "DoesNotExist": _FlagModel.DoesNotExist})
    monkeypatch.setattr(config_ops, "flag_is_active", lambda _request, _name: False, raising=False)

    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, username="tester", id=1))

    import sys
    import types

    waffle_models = types.ModuleType("waffle.models")
    waffle_models.Flag = flag_model
    sys.modules["waffle.models"] = waffle_models

    waffle = types.ModuleType("waffle")
    waffle.flag_is_active = lambda _request, _name: False
    sys.modules["waffle"] = waffle

    assert config_ops.is_owly_chat_enabled_logic(request) == {"enabled": True}


def test_is_owly_chat_enabled_for_anonymous_user(monkeypatch):
    flag_model = type("Flag", (), {"objects": _Manager(_Flag(False)), "DoesNotExist": _FlagModel.DoesNotExist})

    import sys
    import types

    waffle_models = types.ModuleType("waffle.models")
    waffle_models.Flag = flag_model
    sys.modules["waffle.models"] = waffle_models

    waffle = types.ModuleType("waffle")
    waffle.flag_is_active = lambda _request, _name: True
    sys.modules["waffle"] = waffle

    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))

    assert config_ops.is_owly_chat_enabled_logic(request) == {"enabled": True}


def test_is_owly_chat_enabled_returns_false_when_flag_missing():
    flag_model = type("Flag", (), {"objects": _MissingManager(), "DoesNotExist": _FlagModel.DoesNotExist})

    import sys
    import types

    waffle_models = types.ModuleType("waffle.models")
    waffle_models.Flag = flag_model
    sys.modules["waffle.models"] = waffle_models

    waffle = types.ModuleType("waffle")
    waffle.flag_is_active = lambda _request, _name: True
    sys.modules["waffle"] = waffle

    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, username="tester", id=1))

    assert config_ops.is_owly_chat_enabled_logic(request) == {"enabled": False}
