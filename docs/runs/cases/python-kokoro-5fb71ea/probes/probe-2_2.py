import pytest

import api.src.services.tts_service as tts_service_mod
import api.src.inference.model_manager as model_manager_mod
from api.src.services.tts_service import TTSService


@pytest.mark.asyncio
async def test_create_calls_real_model_manager_get_with_no_args(monkeypatch):
    # Ensure a clean singleton state and restore it afterwards.
    prev_instance = model_manager_mod.ModelManager._instance
    model_manager_mod.ModelManager._instance = None
    try:
        # Stub voice manager to avoid any external I/O while keeping model manager real.
        async def fake_get_voice_manager():
            class _VM:
                async def ensure_voice(self, *_, **__):
                    return None
            return _VM()

        monkeypatch.setattr(tts_service_mod, "get_voice_manager", fake_get_voice_manager)

        # Spy on the get_model_manager symbol in TTS service, but execute the real target.
        calls = []
        real_get = model_manager_mod.get_manager

        async def spy_get_manager(*args, **kwargs):
            calls.append((args, kwargs))
            return await real_get(*args, **kwargs)

        monkeypatch.setattr(tts_service_mod, "get_model_manager", spy_get_manager)

        service = await TTSService.create()

        # Verify the spy observed a no-argument call, and the real function executed.
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ()
        assert kwargs == {}
        assert isinstance(service.model_manager, model_manager_mod.ModelManager)
        # The singleton should now be set by the real get_manager
        assert model_manager_mod.ModelManager._instance is service.model_manager
    finally:
        # Restore singleton to avoid leaking state to other tests.
        model_manager_mod.ModelManager._instance = prev_instance
