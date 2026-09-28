import pytest
from unittest.mock import patch


def test_probe_load_voice_grades_calls_core_loader_and_returns_result():
    # Import the module via repo path to access both the function and its in-module collaborator
    import api.src.routers.openai_compatible as openai_mod

    sentinel_result = {"am_adam": {"grade": "A+"}}

    # Patch the direct in-repo collaborator with autospec to record the seam
    with patch.object(
        openai_mod, "_load_core_json", autospec=True, return_value=sentinel_result
    ) as mock_load:
        result = openai_mod.load_voice_grades()

        # Assert delegation and return passthrough
        assert result == sentinel_result
        mock_load.assert_called_once_with("voice_grades.json", {})
