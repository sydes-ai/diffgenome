import pytest

from api.src.inference.model_manager import get_manager, ModelManager


@pytest.mark.asyncio
async def test_get_manager_called_without_args_returns_singleton(monkeypatch):
    # Ensure a cold start so the constructor path is exercised
    monkeypatch.setattr(ModelManager, "_instance", None, raising=False)

    mgr1 = await get_manager()  # called with no arguments, as in TTSService.create
    assert isinstance(mgr1, ModelManager)

    # Subsequent call with no args should return the same singleton instance
    mgr2 = await get_manager()
    assert mgr2 is mgr1
