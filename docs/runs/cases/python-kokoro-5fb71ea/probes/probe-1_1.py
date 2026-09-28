import pytest
from unittest.mock import AsyncMock

from api.src.services.tts_service import TTSService
from api.src.inference.voice_manager import VoiceManager


@pytest.mark.asyncio
async def test_list_voices_executes_real_voice_manager(monkeypatch):
    # Substitute external dependency that would touch the filesystem
    mock_paths_list = AsyncMock(return_value=["alpha", "beta"])
    monkeypatch.setattr(
        "api.src.inference.voice_manager.paths.list_voices", mock_paths_list
    )

    # Provide a real VoiceManager instance to TTSService
    vm = VoiceManager()
    monkeypatch.setattr(
        "api.src.services.tts_service.get_voice_manager", lambda: vm
    )

    # Substitute model manager (unused in this path) to avoid side effects
    monkeypatch.setattr(
        "api.src.services.tts_service.get_model_manager", lambda: object()
    )

    service = await TTSService.create()
    voices = await service.list_voices()

    assert voices == ["alpha", "beta"]
    # Ensure our async dependency was awaited exactly once, proving real method executed
    assert mock_paths_list.await_count == 1
