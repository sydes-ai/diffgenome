# Ambiguous and rejected compositions
seams with >1 accepted continuation shape or with rejected candidates: 109

## api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.inference.model_manager.ModelManager.ensure_backend   [3 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 9}]
  accepted VALUE     api/tests/test_model_unload.py::test_active_request_blocks_idle_unload  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads  no arguments
  … 3 more accepted

## api.src.routers.development.create_captioned_speech ⇢ api.src.routers.openai_compatible.process_and_validate_voices   [3 shapes accepted, +31 same-shape; best=ARG_SHAPE; by grade={'ARG_SHAPE': 34}]
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices_list_input  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices_weighted  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  … 28 more accepted
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_names_are_matched_regardless_of_case  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_names_are_matched_regardless_of_case  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_combine_voices_unknown_voice  outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_dialogue_endpoint_rejects_unknown_voice  outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError
  … 28 more rejected

## api.src.routers.development.create_captioned_speech ⇢ api.src.routers.openai_compatible.process_and_validate_voices   [3 shapes accepted, +31 same-shape; best=ARG_SHAPE; by grade={'ARG_SHAPE': 34}]
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices_list_input  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_combine_voices_weighted  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  accepted ARG_SHAPE api/tests/test_openai_endpoints.py::test_dialogue_endpoint  stand-in argument, type unverified: arg1
  … 28 more accepted
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_names_are_matched_regardless_of_case  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_names_are_matched_regardless_of_case  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag  type conflict: NoneType≠dict[2]
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_combine_voices_unknown_voice  outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError
  REJECTED unsound   api/tests/test_openai_endpoints.py::test_dialogue_endpoint_rejects_unknown_voice  outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError
  … 28 more rejected

## api.src.routers.openai_compatible.get_tts_service ⇢ api.src.services.tts_service.TTSService.create   [3 shapes accepted, +24 same-shape; best=VALUE; by grade={'VALUE': 27}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 21 more accepted

## api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.inference.kokoro_v1.KokoroV1._get_pipeline   [2 shapes accepted, +2 same-shape; best=ARG_SHAPE; by grade={'ARG_SHAPE': 4}]
  accepted ARG_SHAPE api/tests/test_kokoro_v1.py::test_generate_uses_correct_pipeline  values differ: lang_code
  accepted ARG_SHAPE api/tests/test_kokoro_v1.py::test_get_pipeline_creates_new  values differ: lang_code
  accepted ARG_SHAPE api/tests/test_kokoro_v1.py::test_get_pipeline_reuses_existing  values differ: lang_code
  accepted ARG_SHAPE api/tests/test_kokoro_v1.py::test_get_pipeline_reuses_existing  values differ: lang_code

## api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.inference.model_manager.ModelManager.hold   [2 shapes accepted, +2 same-shape; best=VALUE; by grade={'VALUE': 4}]
  accepted VALUE     api/tests/test_model_unload.py::test_active_request_blocks_idle_unload  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_generate_lazy_reinit_when_backend_none  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_generate_schedules_idle_unload_when_enabled  no arguments
  accepted VALUE     api/tests/test_model_unload.py::test_generate_skips_reinit_when_backend_set  no arguments

## api.src.inference.model_manager.ModelManager.ensure_backend ⇢ api.src.inference.model_manager.ModelManager.load_model   [2 shapes accepted, +0 same-shape; best=ARG_SHAPE; by grade={'ARG_SHAPE': 2}]
  accepted ARG_SHAPE api/tests/test_model_unload.py::test_load_model_does_not_schedule_idle_unload_during_active_request  values differ: path
  accepted ARG_SHAPE api/tests/test_model_unload.py::test_load_model_schedules_idle_unload_when_enabled  values differ: path

## api.src.inference.model_manager.ModelManager.ensure_backend ⇢ api.src.inference.model_manager.ModelManager.load_model   [2 shapes accepted, +0 same-shape; best=ARG_SHAPE; by grade={'ARG_SHAPE': 2}]
  accepted ARG_SHAPE api/tests/test_model_unload.py::test_load_model_does_not_schedule_idle_unload_during_active_request  values differ: path
  accepted ARG_SHAPE api/tests/test_model_unload.py::test_load_model_schedules_idle_unload_when_enabled  values differ: path

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager   [2 shapes accepted, +6 same-shape; best=SYMBOL; by grade={'SYMBOL': 8}]
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  accepted SYMBOL    api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  arity differs: arguments on one side only
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager   [2 shapes accepted, +6 same-shape; best=VALUE; by grade={'VALUE': 8}]
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  accepted VALUE     api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400  no arguments
  … 2 more accepted

## all join attempts by grade
  VALUE: 415
  SYMBOL: 152
  ARG_SHAPE: 137
  unsound rejected: 88
