import pytest
from unittest.mock import patch

from api.src.inference.model_manager import ModelManager


class StubBackend:
    def __init__(self):
        self.loaded_paths = []

    async def load_model(self, path):
        self.loaded_paths.append(path)


@pytest.mark.asyncio
async def test_load_model_uses_backend_and_schedules_timer():
    # Arrange: create manager with stubbed backend and patched timer scheduler
    manager = ModelManager()
    backend = StubBackend()
    manager._backend = backend

    expected_path = manager._config.pytorch_kokoro_v1_file

    with patch.object(manager, "_schedule_idle_unload_timer_locked") as schedule_mock:
        # Act: call the real load_model with the same argument ensure_backend would pass
        await manager.load_model(expected_path)

    # Assert: backend received the exact path, last_used_at set, and timer scheduled
    assert backend.loaded_paths == [expected_path]
    assert manager._last_used_at is not None
    schedule_mock.assert_called_once()