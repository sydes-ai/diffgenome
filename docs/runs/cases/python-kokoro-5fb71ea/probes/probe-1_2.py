import pytest
from unittest.mock import AsyncMock

import api.src.inference.voice_manager as voice_manager_mod


@pytest.mark.anyio
async def test_voice_manager_list_voices_uses_paths_list_voices(monkeypatch):
    # Ensure deterministic device selection (avoid GPU probing or env-specific logic)
    monkeypatch.setattr(voice_manager_mod.settings, "get_device", lambda: "cpu", raising=True)

    # Substitute external dependency: filesystem-backed voice discovery
    mocked_list = AsyncMock(return_value=["voiceA", "voiceB"]) 
    monkeypatch.setattr(voice_manager_mod.paths, "list_voices", mocked_list, raising=True)

    vm = voice_manager_mod.VoiceManager()
    voices = await vm.list_voices()

    assert voices == ["voiceA", "voiceB"]
    mocked_list.assert_awaited_once()
