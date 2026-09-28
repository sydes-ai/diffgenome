from unittest.mock import MagicMock, patch

from api.src.inference.kokoro_v1 import KokoroV1


def test_get_pipeline_executes_with_lang_code_and_caches():
    # Create backend and satisfy the loaded-model precondition
    backend = KokoroV1()
    dummy_model = MagicMock(name="DummyModel")
    backend._model = dummy_model

    # Capture constructor args to validate value flow
    captured = {}

    class DummyPipeline:
        def __init__(self, lang_code, repo_id, model, device):
            captured["lang_code"] = lang_code
            captured["repo_id"] = repo_id
            captured["model"] = model
            captured["device"] = device

    # Patch external dependencies: KPipeline and settings.model_repo_id
    with (
        patch("api.src.inference.kokoro_v1.KPipeline", DummyPipeline),
        patch("api.src.inference.kokoro_v1.settings") as mock_settings,
    ):
        mock_settings.model_repo_id = "fake/repo"

        # Execute the real in-repo target with the same value shape used by TTSService path
        lang_code = "a"
        pipe1 = backend._get_pipeline(lang_code)

        # Validate values propagated into the (stubbed) pipeline and caching behavior
        assert isinstance(pipe1, DummyPipeline)
        assert captured["lang_code"] == lang_code
        assert captured["repo_id"] == "fake/repo"
        assert captured["model"] is dummy_model
        assert captured["device"] == backend._device

        # Second call with same lang_code should return cached instance
        pipe2 = backend._get_pipeline(lang_code)
        assert pipe2 is pipe1
