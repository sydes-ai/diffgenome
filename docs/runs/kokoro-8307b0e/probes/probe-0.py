import pytest
from unittest.mock import AsyncMock, patch

from api.src.inference.model_manager import ModelManager


@pytest.mark.asyncio
async def test_initialize_runs_via_ensure_backend_with_substitutions():
    """Ensure real initialize executes via ensure_backend with externals stubbed.

    Substitutes torch (device detection), KokoroV1 (heavy backend), and load_model (I/O)
    so that initialize can run deterministically and fast.
    """
    manager = ModelManager()
    assert manager._backend is None

    with (
        patch("api.src.inference.model_manager.torch") as mock_torch,
        patch("api.src.inference.model_manager.KokoroV1") as mock_kokoro,
        patch.object(manager, "load_model", new_callable=AsyncMock) as mock_load,
    ):
        # Force CPU path and avoid any CUDA/GPU probing.
        mock_torch.cuda.is_available.return_value = False

        await manager.ensure_backend()

    # Real initialize should have constructed the backend once and stored it.
    mock_kokoro.assert_called_once_with()
    assert manager._backend is mock_kokoro.return_value

    # ensure_backend should proceed to (mocked) load_model with the configured file path.
    mock_load.assert_awaited_once_with(manager._config.pytorch_kokoro_v1_file)
