# diffgenome behavioral impact report

Change: git diff 8307b0e
Changed symbols (37):
  api.src.core.config.Settings  executed by 0 test(s)  ← no existing execution
  api.src.inference.model_manager.ModelManager  executed by 0 test(s)  ← no existing execution
  api.src.inference.model_manager.ModelManager.__init__  executed by 15 test(s)
  api.src.inference.model_manager.ModelManager.ensure_backend  executed by 5 test(s)
  api.src.inference.model_manager.ModelManager.load_model  executed by 2 test(s)
  api.src.inference.model_manager.ModelManager._auto_unload_timeout  executed by 8 test(s)
  api.src.inference.model_manager.ModelManager._format_seconds  executed by 3 test(s)
  api.src.inference.model_manager.ModelManager._auto_unload_enabled  executed by 8 test(s)
  api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  executed by 11 test(s)
  api.src.inference.model_manager.ModelManager._unload_backend_locked  executed by 7 test(s)
  api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  executed by 6 test(s)
  api.src.inference.model_manager.ModelManager._idle_unload_after  executed by 3 test(s)
  api.src.inference.model_manager.ModelManager._begin_request  executed by 4 test(s)
  api.src.inference.model_manager.ModelManager._end_request  executed by 4 test(s)
  api.src.inference.model_manager.ModelManager.hold  executed by 4 test(s)
  api.src.inference.model_manager.ModelManager.generate  executed by 4 test(s)
  api.src.inference.model_manager.ModelManager.unload_all  executed by 0 test(s)  ← no existing execution
  api.src.inference.model_manager.ModelManager.unload  executed by 4 test(s)
  api.src.inference.model_manager.ModelManager.reload  executed by 0 test(s)  ← no existing execution
  api.src.inference.model_manager.ModelManager.status  executed by 1 test(s)
  api.src.routers.development.reload_model  executed by 1 test(s)
  api.src.routers.development.model_status  executed by 1 test(s)
  api.src.services.tts_service.TTSService.generate_from_phonemes  executed by 1 test(s)
  api.tests.test_model_unload._enable_dev_unload  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_manager_init_creates_lock  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled.<locals>.fake_generate  executed by 1 test(s)
  api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_active_request_blocks_idle_unload  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_active_request_blocks_idle_unload.<locals>.slow_generate  executed by 1 test(s)
  api.tests.test_model_unload.test_status_reports_model_lifecycle_state  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_reload_endpoint_returns_status  executed by 0 test(s)  ← no existing execution
  api.tests.test_model_unload.test_model_status_endpoint_returns_status  executed by 0 test(s)  ← no existing execution
  api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code  executed by 0 test(s)  ← no existing execution
  api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code.<locals>.noop_hold  executed by 1 test(s)
Changed files with no mapped code symbol: CHANGELOG.md, README.md, docs/configuration.md

## Behavioral neighborhood (before probes)

### Upstream (what reaches the change)
  d1  api.src.inference.model_manager.ModelManager._auto_unload_enabled → api.src.inference.model_manager.ModelManager._auto_unload_timeout  tests=8
  d1  api.src.inference.model_manager.ModelManager._begin_request → api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  tests=4
  d1  api.src.inference.model_manager.ModelManager._end_request → api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  tests=4
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → api.src.inference.model_manager.ModelManager._auto_unload_enabled  tests=3
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → api.src.inference.model_manager.ModelManager._auto_unload_timeout  tests=3
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → api.src.inference.model_manager.ModelManager._format_seconds  tests=3
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → api.src.inference.model_manager.ModelManager._unload_backend_locked  tests=3
  d1  api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked → api.src.inference.model_manager.ModelManager._auto_unload_enabled  tests=6
  d1  api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked → api.src.inference.model_manager.ModelManager._auto_unload_timeout  tests=3
  d1  api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked → api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  tests=6
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  tests=2
  d1  api.src.inference.model_manager.ModelManager.ensure_backend ⇢ api.src.inference.model_manager.ModelManager.load_model  tests=4  join=arg_shape  rule=claim-member
  d1  api.src.inference.model_manager.ModelManager.generate → api.src.inference.model_manager.ModelManager.ensure_backend  tests=4
  d1  api.src.inference.model_manager.ModelManager.generate → api.src.inference.model_manager.ModelManager.hold  tests=4
  d1  api.src.inference.model_manager.ModelManager.hold → api.src.inference.model_manager.ModelManager._begin_request  tests=4
  d1  api.src.inference.model_manager.ModelManager.hold → api.src.inference.model_manager.ModelManager._end_request  tests=4
  d1  api.src.inference.model_manager.ModelManager.load_model → api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  tests=2
  d1  api.src.inference.model_manager.ModelManager.status → api.src.inference.model_manager.ModelManager._auto_unload_enabled  tests=1
  d1  api.src.inference.model_manager.ModelManager.status → api.src.inference.model_manager.ModelManager._auto_unload_timeout  tests=1
  d1  api.src.inference.model_manager.ModelManager.unload → api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  tests=4
  d1  api.src.inference.model_manager.ModelManager.unload → api.src.inference.model_manager.ModelManager._unload_backend_locked  tests=4
  d1  api.src.inference.model_manager.get_manager → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_active_request_blocks_idle_unload → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_active_request_blocks_idle_unload → api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  tests=1
  d1  api.tests.test_model_unload.test_active_request_blocks_idle_unload → api.src.inference.model_manager.ModelManager.generate  tests=1
  d1  api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads → api.src.inference.model_manager.ModelManager.ensure_backend  tests=1
  d1  api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none → api.src.inference.model_manager.ModelManager.generate  tests=1
  d1  api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager._idle_unload_after  tests=1
  d1  api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager.generate  tests=1
  d1  api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set → api.src.inference.model_manager.ModelManager.generate  tests=1
  d1  api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout → api.src.inference.model_manager.ModelManager._idle_unload_after  tests=1
  d1  api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request → api.src.inference.model_manager.ModelManager.load_model  tests=1
  d1  api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager._idle_unload_after  tests=1
  d1  api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled → api.src.inference.model_manager.ModelManager.load_model  tests=1
  d1  api.tests.test_model_unload.test_manager_init_creates_lock → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_model_status_endpoint_returns_status → api.src.routers.development.model_status  tests=1
  d1  api.tests.test_model_unload.test_reload_endpoint_returns_status → api.src.routers.development.reload_model  tests=1
  d1  api.tests.test_model_unload.test_status_reports_model_lifecycle_state → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_status_reports_model_lifecycle_state → api.src.inference.model_manager.ModelManager.status  tests=1
  d1  api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available → api.src.inference.model_manager.ModelManager.unload  tests=1
  d1  api.tests.test_model_unload.test_unload_clears_backend → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_unload_clears_backend → api.src.inference.model_manager.ModelManager.unload  tests=1
  d1  api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable → api.src.inference.model_manager.ModelManager.unload  tests=1
  d1  api.tests.test_model_unload.test_unload_when_already_none_is_noop → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d1  api.tests.test_model_unload.test_unload_when_already_none_is_noop → api.src.inference.model_manager.ModelManager.unload  tests=1
  d1  api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code → api.src.services.tts_service.TTSService.generate_from_phonemes  tests=1
  d2  api.src.services.tts_service.TTSService.create → api.src.inference.model_manager.get_manager  tests=6
  d2  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member
  d3  api.src.routers.development.get_tts_service → api.src.services.tts_service.TTSService.create  tests=6
  d3  api.src.routers.openai_compatible.get_tts_service ⇢ api.src.services.tts_service.TTSService.create  tests=26  join=value  rule=claim-member
  d3  api.tests.test_tts_service._stubbed_service → api.src.services.tts_service.TTSService.create  tests=8

### Downstream (what continues from the change)
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] loguru._logger.Logger.info  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] torch.cuda.is_available  tests=3  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._unload_backend_locked → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._unload_backend_locked → [unresolved] py:unittest.mock.MagicMock.unload  tests=6  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [gap] api.src.inference.model_manager.ModelManager.initialize  tests=2  rule=claim-member
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_load  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_active_request_blocks_idle_unload.<locals>.slow_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.load_model → [unresolved] py:unittest.mock.AsyncMock.load_model  tests=2  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.status → api.src.inference.model_manager.ModelManager.current_backend  tests=1
  d1  api.src.inference.model_manager.ModelManager.status → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager.unload → [external] torch.cuda.empty_cache  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager.unload → [external] torch.cuda.is_available  tests=4  rule=claim-outside-repo
  d1  api.src.routers.development.model_status → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
  d1  api.src.routers.development.reload_model → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.inference.kokoro_v1.KokoroV1._get_pipeline  tests=4  join=arg_shape  rule=claim-member
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.kokoro_v1.KokoroV1._get_pipeline.().generate_from_tokens  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().ensure_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().get_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().hold  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.services.tts_service.TTSService.get_voices_path  tests=4  join=arg_shape  rule=claim-member
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] py:api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code.<locals>.noop_hold  tests=1  rule=no-claim
  d2  api.src.inference.kokoro_v1.KokoroV1._get_pipeline → [external] kokoro.pipeline.KPipeline.__init__  tests=3  rule=claim-outside-repo
  d2  api.src.services.tts_service.TTSService.get_voices_path → [unresolved] api.src.inference.voice_manager.get_manager.().get_voice_path  tests=3  rule=claim-return-chain
  d2  api.src.services.tts_service.TTSService.get_voices_path → api.src.services.tts_service.TTSService._load_voice_from_path  tests=1
  d2  api.src.services.tts_service.TTSService.get_voices_path → [external] tempfile.gettempdir  tests=1  rule=claim-outside-repo
  d2  api.src.services.tts_service.TTSService.get_voices_path → [external] torch.serialization.save  tests=1  rule=claim-outside-repo
  d3  api.src.services.tts_service.TTSService._load_voice_from_path → [external] torch.serialization.load  tests=1  rule=claim-outside-repo

### Tests establishing these paths (45)
  api/tests/test_kokoro_v1.py::test_generate_uses_correct_pipeline
  api/tests/test_kokoro_v1.py::test_get_pipeline_creates_new
  api/tests/test_kokoro_v1.py::test_get_pipeline_reuses_existing
  api/tests/test_model_unload.py::test_active_request_blocks_idle_unload
  api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads
  api/tests/test_model_unload.py::test_generate_lazy_reinit_when_backend_none
  api/tests/test_model_unload.py::test_generate_schedules_idle_unload_when_enabled
  api/tests/test_model_unload.py::test_generate_skips_reinit_when_backend_set
  api/tests/test_model_unload.py::test_idle_auto_unload_log_includes_configured_timeout
  api/tests/test_model_unload.py::test_load_model_does_not_schedule_idle_unload_during_active_request
  api/tests/test_model_unload.py::test_load_model_schedules_idle_unload_when_enabled
  api/tests/test_model_unload.py::test_manager_init_creates_lock
  api/tests/test_model_unload.py::test_model_status_endpoint_returns_status
  api/tests/test_model_unload.py::test_reload_endpoint_returns_status
  api/tests/test_model_unload.py::test_status_reports_model_lifecycle_state
  api/tests/test_model_unload.py::test_unload_calls_cuda_empty_cache_when_available
  api/tests/test_model_unload.py::test_unload_clears_backend
  api/tests/test_model_unload.py::test_unload_skips_cuda_empty_cache_when_unavailable
  api/tests/test_model_unload.py::test_unload_when_already_none_is_noop
  api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled
  api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input
  api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected
  api/tests/test_openai_endpoints.py::test_captioned_streaming_over_pause_budget_is_400
  api/tests/test_openai_endpoints.py::test_get_tts_service_initialization
  api/tests/test_openai_endpoints.py::test_malformed_ssml_on_the_captioned_endpoint_is_a_400
  api/tests/test_openai_endpoints.py::test_ssml_kill_switch_403s_the_captioned_endpoint
  api/tests/test_tts_service.py::test_generate_audio_joins_encoded_chunks
  api/tests/test_tts_service.py::test_generate_audio_with_nothing_speakable_raises
  api/tests/test_tts_service.py::test_generate_from_phonemes_uses_default_voice_code
  api/tests/test_tts_service.py::test_get_voice_path_combined
  api/tests/test_tts_service.py::test_get_voice_path_single
  api/tests/test_tts_service.py::test_get_voice_path_single_with_weight_normalized
  api/tests/test_tts_service.py::test_list_voices
  api/tests/test_tts_service.py::test_pause_budget_survives_voice_tag_segmentation
  api/tests/test_tts_service.py::test_rate_tags_multiply_request_speed
  api/tests/test_tts_service.py::test_service_creation
  api/tests/test_tts_service.py::test_split_multi_voice_default_voice_code_used_when_no_lang_code
  api/tests/test_tts_service.py::test_split_multi_voice_explicit_lang_code_beats_default
  api/tests/test_tts_service.py::test_split_multi_voice_explicit_lang_code_wins
  api/tests/test_tts_service.py::test_split_multi_voice_lang_code_per_speaker
  ... 5 more

## Where knowledge stops (before probes)
### internal_gap (3)
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [gap] api.src.inference.model_manager.ModelManager.initialize  tests=2  rule=claim-member
  d1  api.src.routers.development.model_status → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
  d1  api.src.routers.development.reload_model → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
### unresolved_boundary (15)
  d1  api.src.inference.model_manager.ModelManager._unload_backend_locked → [unresolved] py:unittest.mock.MagicMock.unload  tests=6  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_load  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_active_request_blocks_idle_unload.<locals>.slow_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.load_model → [unresolved] py:unittest.mock.AsyncMock.load_model  tests=2  rule=no-claim
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.kokoro_v1.KokoroV1._get_pipeline.().generate_from_tokens  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().ensure_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().get_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().hold  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] py:api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code.<locals>.noop_hold  tests=1  rule=no-claim
  d2  api.src.services.tts_service.TTSService.get_voices_path → [unresolved] api.src.inference.voice_manager.get_manager.().get_voice_path  tests=3  rule=claim-return-chain
### external_boundary (11)
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] loguru._logger.Logger.info  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._idle_unload_after → [external] torch.cuda.is_available  tests=3  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager._unload_backend_locked → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager.status → [external] time.monotonic  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager.unload → [external] torch.cuda.empty_cache  tests=1  rule=claim-outside-repo
  d1  api.src.inference.model_manager.ModelManager.unload → [external] torch.cuda.is_available  tests=4  rule=claim-outside-repo
  d2  api.src.inference.kokoro_v1.KokoroV1._get_pipeline → [external] kokoro.pipeline.KPipeline.__init__  tests=3  rule=claim-outside-repo
  d2  api.src.services.tts_service.TTSService.get_voices_path → [external] tempfile.gettempdir  tests=1  rule=claim-outside-repo
  d2  api.src.services.tts_service.TTSService.get_voices_path → [external] torch.serialization.save  tests=1  rule=claim-outside-repo
  d3  api.src.services.tts_service.TTSService._load_voice_from_path → [external] torch.serialization.load  tests=1  rule=claim-outside-repo
### weak joins (4)
  d1  api.src.inference.model_manager.ModelManager.ensure_backend ⇢ api.src.inference.model_manager.ModelManager.load_model  tests=4  join=arg_shape  rule=claim-member
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.inference.kokoro_v1.KokoroV1._get_pipeline  tests=4  join=arg_shape  rule=claim-member
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.services.tts_service.TTSService.get_voices_path  tests=4  join=arg_shape  rule=claim-member
  d2  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member

## Generated probes
- objective: internal_gap api.src.inference.model_manager.ModelManager.initialize (from api.src.inference.model_manager.ModelManager.ensure_backend, d1)
  attempt 1: accepted  model=recorded
  learned 5 observed edge(s):
    + py:api.src.inference.model_manager.ModelManager.ensure_backend → py:api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer [returned]
    + py:api.src.inference.model_manager.ModelManager.ensure_backend → py:api.src.inference.model_manager.ModelManager.initialize [returned]
    + py:api.src.inference.model_manager.ModelManager.initialize → py:api.src.inference.model_manager.ModelManager._determine_device [returned]
    + py:api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions → py:api.src.inference.model_manager.ModelManager.__init__ [returned]
    + py:api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions → py:api.src.inference.model_manager.ModelManager.ensure_backend [returned]
- objective: weak_join api.src.inference.model_manager.ModelManager.load_model (from api.src.inference.model_manager.ModelManager.ensure_backend, d1)
  attempt 1: accepted  model=recorded
  learned 3 observed edge(s):
    + py:api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer → py:api.src.inference.model_manager.ModelManager.__init__ [returned]
    + py:api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer → py:api.src.inference.model_manager.ModelManager.load_model [returned]
    + py:api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer → py:api.tests.test_diffgenome_probe_1_1.StubBackend.__init__ [returned]
- objective: weak_join api.src.inference.kokoro_v1.KokoroV1._get_pipeline (from api.src.services.tts_service.TTSService.generate_from_phonemes, d1)
  attempt 1: accepted  model=recorded
  learned 5 observed edge(s):
    + py:api.src.inference.kokoro_v1.KokoroV1.__init__ → py:api.src.core.config.Settings.get_device [returned]
    + py:api.src.inference.kokoro_v1.KokoroV1.__init__ → py:api.src.inference.base.BaseModelBackend.__init__ [returned]
    + py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches → py:api.src.inference.kokoro_v1.KokoroV1.__init__ [returned]
    + py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches → py:api.src.inference.kokoro_v1.KokoroV1._get_pipeline [returned]
    + py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches → py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches.<locals>.DummyPipeline [returned]

## Before vs after
| metric | before | after |
|---|---|---|
| observed edges | 70 | 78 |
| composed edges | 5 | 8 |
| strong joins (VALUE+) | 1 | 6 |
| weak joins | 4 | 2 |
| internal gaps | 3 | 2 |
| unresolved boundaries | 15 | 17 |
| external boundaries | 11 | 11 |
| os boundaries | 0 | 0 |
| unsound attempts | 0 | 0 |
| probe-derived edges | 0 | 16 |
| symbols | 84 | 92 |
| tests | 45 | 48 |
| reconstructed / provisional denominator | 71/93 = 0.763 | 84/105 = 0.800 |

Denominator is provisional: observed + composed edges + internal gaps + unresolved
stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior
no execution has come near, and external/OS boundaries, which are terminal by design.

## Remaining after probes
### internal_gap (2)
  d1  api.src.routers.development.model_status → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
  d1  api.src.routers.development.reload_model → [gap] api.src.services.tts_service.TTSService  tests=1  rule=claim-member
### unresolved_boundary (17)
  d1  api.src.inference.model_manager.ModelManager._unload_backend_locked → [unresolved] py:unittest.mock.MagicMock.unload  tests=6  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_load  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.ensure_backend → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_initialize  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_active_request_blocks_idle_unload.<locals>.slow_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.generate → [unresolved] py:api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set.<locals>.fake_generate  tests=1  rule=no-claim
  d1  api.src.inference.model_manager.ModelManager.load_model → [unresolved] py:api.tests.test_diffgenome_probe_1_1.StubBackend.load_model  tests=1  rule=no-claim  probe-derived
  d1  api.src.inference.model_manager.ModelManager.load_model → [unresolved] py:unittest.mock.AsyncMock.load_model  tests=2  rule=no-claim
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.kokoro_v1.KokoroV1._get_pipeline.().generate_from_tokens  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().ensure_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().get_backend  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] api.src.inference.model_manager.get_manager.().hold  tests=1  rule=claim-return-chain
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes → [unresolved] py:api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code.<locals>.noop_hold  tests=1  rule=no-claim
  d2  api.src.inference.kokoro_v1.KokoroV1._get_pipeline → [unresolved] py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches.<locals>.DummyPipeline.__init__  tests=1  rule=no-claim  probe-derived
  d2  api.src.services.tts_service.TTSService.get_voices_path → [unresolved] api.src.inference.voice_manager.get_manager.().get_voice_path  tests=3  rule=claim-return-chain
### weak joins (2)
  d1  api.src.services.tts_service.TTSService.generate_from_phonemes ⇢ api.src.services.tts_service.TTSService.get_voices_path  tests=4  join=arg_shape  rule=claim-member
  d2  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member

## Notes
- 4 changed symbol(s) have no existing execution at all: api.src.core.config.Settings, api.src.inference.model_manager.ModelManager, api.src.inference.model_manager.ModelManager.unload_all, api.src.inference.model_manager.ModelManager.reload
- not probeable: py:api.src.services.tts_service.TTSService: class construction with no in-repo __init__
