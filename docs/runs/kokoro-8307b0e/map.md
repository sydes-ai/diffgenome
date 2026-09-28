legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  → [unresolved] stand-in not resolved  → [external] outside the repository  → [os] kernel boundary

# api.src.core.config.Settings  [origin=unknown executed_by=0 outcomes={}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  (no observed or composed caller)
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager  [origin=unknown executed_by=0 outcomes={}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  (no observed or composed caller)
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager.__init__  [origin=repo executed_by=17 outcomes={'returned': 17}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.get_manager →  [observed outcomes=returned:17 tests=1]
  │  ├api.src.services.tts_service.TTSService.create ⇢  [composed join=symbol +114 same-shape rule=claim-member outcomes=returned:8 tests=25]
  │  │  ├api.src.routers.openai_compatible.get_tts_service ⇢  [composed join=value +24 same-shape rule=claim-member outcomes=returned:27 tests=26]
  │  │  ├api.src.routers.development.get_tts_service →  [observed outcomes=returned:27 tests=6]
  │  │  ├api.tests.test_tts_service._stubbed_service →  [observed outcomes=returned:27 tests=8]
  │  │  ├api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_get_voice_path_combined →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_get_voice_path_single →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_get_voice_path_single_with_weight_normalized →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_list_voices →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_service_creation →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_split_multi_voice_default_voice_code_used_when_no_lang_code →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_split_multi_voice_explicit_lang_code_beats_default →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_split_multi_voice_explicit_lang_code_wins →  [observed outcomes=returned:27 tests=1]
  │  │  ├api.tests.test_tts_service.test_split_multi_voice_lang_code_per_speaker →  [observed outcomes=returned:27 tests=1]
  │  │  └api.tests.test_tts_service.test_split_multi_voice_resolves_each_speaker_once →  [observed outcomes=returned:27 tests=1]
  │  └api.src.services.tts_service.TTSService.create →  [observed outcomes=returned:8 tests=6]
  │     ├api.src.routers.openai_compatible.get_tts_service ⇢  [composed join=value +24 same-shape rule=claim-member outcomes=returned:27 tests=26]
  │     ├api.src.routers.development.get_tts_service →  [observed outcomes=returned:27 tests=6]
  │     ├api.tests.test_tts_service._stubbed_service →  [observed outcomes=returned:27 tests=8]
  │     ├api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_get_voice_path_combined →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_get_voice_path_single →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_get_voice_path_single_with_weight_normalized →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_list_voices →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_service_creation →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_split_multi_voice_default_voice_code_used_when_no_lang_code →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_split_multi_voice_explicit_lang_code_beats_default →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_split_multi_voice_explicit_lang_code_wins →  [observed outcomes=returned:27 tests=1]
  │     ├api.tests.test_tts_service.test_split_multi_voice_lang_code_per_speaker →  [observed outcomes=returned:27 tests=1]
  │     └api.tests.test_tts_service.test_split_multi_voice_resolves_each_speaker_once →  [observed outcomes=returned:27 tests=1]
  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:17 tests=1 probe-derived]
  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:17 tests=1 probe-derived]
  ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_manager_init_creates_lock →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_status_reports_model_lifecycle_state →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_unload_clears_backend →  [observed outcomes=returned:17 tests=1]
  ├api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable →  [observed outcomes=returned:17 tests=1]
  └api.tests.test_model_unload.test_unload_when_already_none_is_noop →  [observed outcomes=returned:17 tests=1]
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager.ensure_backend  [origin=repo executed_by=6 outcomes={'returned': 10}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:10 tests=4]
  │  ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
  │  └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:10 tests=1 probe-derived]
  └api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:10 tests=1]
## downstream (what continues from it)
  ├⇢ api.src.inference.model_manager.ModelManager.initialize  [composed join=value rule=claim-member outcomes=returned:1 tests=3 probe-derived]
  │  ├⇢ api.src.inference.kokoro_v1.KokoroV1.__init__  [composed join=value rule=claim-member outcomes=returned:1 tests=2 probe-derived]
  │  │  ├→ api.src.core.config.Settings.get_device  [observed outcomes=returned:2 tests=1 probe-derived]
  │  │  └→ api.src.inference.base.BaseModelBackend.__init__  [observed outcomes=returned:1 tests=1 probe-derived]
  │  └→ api.src.inference.model_manager.ModelManager._determine_device  [observed outcomes=returned:1 tests=1 probe-derived]
  ├⇢ api.src.inference.model_manager.ModelManager.load_model  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  ├⇢ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  │  ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=6]
  │  │  │  └→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=8]
  │  │  ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=3]
  │  │  └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=6]
  │  ├→ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [observed outcomes=returned:6 tests=2]
  │  │  ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=6]  (see above)
  │  │  ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=3]  (see above)
  │  │  └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=6]  (see above)
  │  ├→ [unresolved] py:api.tests.test_diffgenome_probe_1_1.StubBackend.load_model  [unresolved_boundary rule=no-claim tests=1 probe-derived]
  │  └→ [unresolved] py:unittest.mock.AsyncMock.load_model  [unresolved_boundary rule=no-claim tests=2]
  ├→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=3 probe-derived]
  ├→ api.src.inference.model_manager.ModelManager.initialize  [observed outcomes=returned:1 tests=1 probe-derived]
  │  ├⇢ api.src.inference.kokoro_v1.KokoroV1.__init__  [composed join=value rule=claim-member outcomes=returned:1 tests=2 probe-derived]  (see above)
  │  └→ api.src.inference.model_manager.ModelManager._determine_device  [observed outcomes=returned:1 tests=1 probe-derived]  (see above)
  ├→ [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_initialize  [unresolved_boundary rule=no-claim tests=1]
  ├→ [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_load  [unresolved_boundary rule=no-claim tests=1]
  └→ [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_initialize  [unresolved_boundary rule=no-claim tests=1]

# api.src.inference.model_manager.ModelManager.load_model  [origin=repo executed_by=3 outcomes={'returned': 3}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  ├api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:10 tests=4]
  │  │  ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
  │  │  ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
  │  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
  │  │  └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:10 tests=1 probe-derived]
  │  └api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:10 tests=1]
  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  ├⇢ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]  (see above)
  ├→ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [observed outcomes=returned:6 tests=2]  (see above)
  ├→ [unresolved] py:api.tests.test_diffgenome_probe_1_1.StubBackend.load_model  [unresolved_boundary rule=no-claim tests=1 probe-derived]  (see above)
  └→ [unresolved] py:unittest.mock.AsyncMock.load_model  [unresolved_boundary rule=no-claim tests=2]  (see above)

# api.src.inference.model_manager.ModelManager._auto_unload_timeout  [origin=repo executed_by=8 outcomes={'returned': 21}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager._auto_unload_enabled →  [observed outcomes=returned:21 tests=8]
  │  ├api.src.inference.model_manager.ModelManager._idle_unload_after →  [observed outcomes=returned:11 tests=3]
  │  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  │  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
  │  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked →  [observed outcomes=returned:11 tests=6]
  │  │  ├api.src.inference.model_manager.ModelManager.load_model ⇢  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  │  ├api.src.inference.model_manager.ModelManager._end_request →  [observed outcomes=returned:6 tests=4]
  │  │  └api.src.inference.model_manager.ModelManager.load_model →  [observed outcomes=returned:6 tests=2]
  │  └api.src.inference.model_manager.ModelManager.status →  [observed outcomes=returned:11 tests=1]
  │     └api.tests.test_model_unload.test_status_reports_model_lifecycle_state →  [observed outcomes=returned:1 tests=1]
  ├api.src.inference.model_manager.ModelManager._idle_unload_after →  [observed outcomes=returned:21 tests=3]
  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  ├api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked →  [observed outcomes=returned:21 tests=3]
  │  ├api.src.inference.model_manager.ModelManager.load_model ⇢  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  │  ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  │  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  │  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.src.inference.model_manager.ModelManager._end_request →  [observed outcomes=returned:6 tests=4]
  │  │  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
  │  └api.src.inference.model_manager.ModelManager.load_model →  [observed outcomes=returned:6 tests=2]
  │     ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │     ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │     ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │     └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  └api.src.inference.model_manager.ModelManager.status →  [observed outcomes=returned:21 tests=1]
     └api.tests.test_model_unload.test_status_reports_model_lifecycle_state →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager._format_seconds  [origin=repo executed_by=3 outcomes={'returned': 3}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.src.inference.model_manager.ModelManager._idle_unload_after →  [observed outcomes=returned:3 tests=3]
     ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
     ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
     └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager._auto_unload_enabled  [origin=repo executed_by=8 outcomes={'returned': 11}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager._idle_unload_after →  [observed outcomes=returned:11 tests=3]
  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  ├api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked →  [observed outcomes=returned:11 tests=6]
  │  ├api.src.inference.model_manager.ModelManager.load_model ⇢  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  │  ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  │  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  │  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.src.inference.model_manager.ModelManager._end_request →  [observed outcomes=returned:6 tests=4]
  │  │  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
  │  └api.src.inference.model_manager.ModelManager.load_model →  [observed outcomes=returned:6 tests=2]
  │     ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │     ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │     ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │     └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  └api.src.inference.model_manager.ModelManager.status →  [observed outcomes=returned:11 tests=1]
     └api.tests.test_model_unload.test_status_reports_model_lifecycle_state →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  └→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=8]  (see above)

# api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [origin=repo executed_by=12 outcomes={'returned': 18}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager._begin_request →  [observed outcomes=returned:18 tests=4]
  │  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
  │     └api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:4 tests=4]
  ├api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked →  [observed outcomes=returned:18 tests=6]
  │  ├api.src.inference.model_manager.ModelManager.load_model ⇢  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  │  ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  │  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  │  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.src.inference.model_manager.ModelManager._end_request →  [observed outcomes=returned:6 tests=4]
  │  │  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
  │  └api.src.inference.model_manager.ModelManager.load_model →  [observed outcomes=returned:6 tests=2]
  │     ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │     ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │     ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │     └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  ├api.src.inference.model_manager.ModelManager.ensure_backend →  [observed outcomes=returned:18 tests=3 probe-derived]
  │  ├api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:10 tests=4]
  │  │  ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
  │  │  ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
  │  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
  │  │  └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:10 tests=1 probe-derived]
  │  └api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:10 tests=1]
  ├api.src.inference.model_manager.ModelManager.unload →  [observed outcomes=returned:18 tests=4]
  │  ├api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_model_unload.test_unload_clears_backend →  [observed outcomes=returned:4 tests=1]
  │  ├api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable →  [observed outcomes=returned:4 tests=1]
  │  └api.tests.test_model_unload.test_unload_when_already_none_is_noop →  [observed outcomes=returned:4 tests=1]
  └api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:18 tests=1]
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager._unload_backend_locked  [origin=repo executed_by=7 outcomes={'returned': 7}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager._idle_unload_after →  [observed outcomes=returned:7 tests=3]
  │  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  │  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  └api.src.inference.model_manager.ModelManager.unload →  [observed outcomes=returned:7 tests=4]
     ├api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available →  [observed outcomes=returned:4 tests=1]
     ├api.tests.test_model_unload.test_unload_clears_backend →  [observed outcomes=returned:4 tests=1]
     ├api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable →  [observed outcomes=returned:4 tests=1]
     └api.tests.test_model_unload.test_unload_when_already_none_is_noop →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  ├→ [external] time.monotonic  [external_boundary rule=claim-outside-repo tests=1]
  └→ [unresolved] py:unittest.mock.MagicMock.unload  [unresolved_boundary rule=no-claim tests=6]

# api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [origin=repo executed_by=6 outcomes={'returned': 6}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.inference.model_manager.ModelManager.load_model ⇢  [composed join=value +4 same-shape rule=claim-member outcomes=returned:6 tests=7 probe-derived]
  │  ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
  │  │  ├api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:10 tests=4]
  │  │  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:10 tests=1 probe-derived]
  │  │  └api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:10 tests=1]
  │  ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
  │  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  ├api.src.inference.model_manager.ModelManager._end_request →  [observed outcomes=returned:6 tests=4]
  │  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
  │     └api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:4 tests=4]
  └api.src.inference.model_manager.ModelManager.load_model →  [observed outcomes=returned:6 tests=2]
     ├api.src.inference.model_manager.ModelManager.ensure_backend ⇢  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]
     │  ├api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:10 tests=4]
     │  ├api.tests.test_diffgenome_probe_0_1.test_initialize_runs_via_ensure_backend_with_substitutions →  [observed outcomes=returned:10 tests=1 probe-derived]
     │  └api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads →  [observed outcomes=returned:10 tests=1]
     ├api.tests.test_diffgenome_probe_1_1.test_load_model_uses_backend_and_schedules_timer →  [observed outcomes=returned:3 tests=1 probe-derived]
     ├api.tests.test_model_unload.test_load_model_does_not_schedule_idle_unload_during_active_request →  [observed outcomes=returned:3 tests=1]
     └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=6]  (see above)
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=3]  (see above)
  └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=6]  (see above)

# api.src.inference.model_manager.ModelManager._idle_unload_after  [origin=repo executed_by=3 outcomes={'returned': 3}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
  ├api.tests.test_model_unload.test_idle_auto_unload_log_includes_configured_timeout →  [observed outcomes=returned:3 tests=1]
  └api.tests.test_model_unload.test_load_model_schedules_idle_unload_when_enabled →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  ├→ [external] loguru._logger.Logger.info  [external_boundary rule=claim-outside-repo tests=1]
  ├→ [external] time.monotonic  [external_boundary rule=claim-outside-repo tests=1]
  ├→ [external] torch.cuda.is_available  [external_boundary rule=claim-outside-repo tests=3]
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=3]
  │  └→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=8]  (see above)
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=3]
  ├→ api.src.inference.model_manager.ModelManager._format_seconds  [observed outcomes=returned:3 tests=3]
  └→ api.src.inference.model_manager.ModelManager._unload_backend_locked  [observed outcomes=returned:7 tests=3]
     ├→ [external] time.monotonic  [external_boundary rule=claim-outside-repo tests=1]  (see above)
     └→ [unresolved] py:unittest.mock.MagicMock.unload  [unresolved_boundary rule=no-claim tests=6]  (see above)

# api.src.inference.model_manager.ModelManager._begin_request  [origin=repo executed_by=4 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
     └api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:4 tests=4]
        ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
        ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
        ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
        └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=4]

# api.src.inference.model_manager.ModelManager._end_request  [origin=repo executed_by=4 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.src.inference.model_manager.ModelManager.hold →  [observed outcomes=returned:4 tests=4]
     └api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:4 tests=4]
        ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
        ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
        ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
        └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  └→ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [observed outcomes=returned:6 tests=4]
     ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=6]  (see above)
     ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=3]  (see above)
     └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=6]  (see above)

# api.src.inference.model_manager.ModelManager.hold  [origin=repo executed_by=4 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.src.inference.model_manager.ModelManager.generate →  [observed outcomes=returned:4 tests=4]
     ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
     ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
     ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
     └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  ├→ api.src.inference.model_manager.ModelManager._begin_request  [observed outcomes=returned:4 tests=4]
  │  └→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=4]  (see above)
  └→ api.src.inference.model_manager.ModelManager._end_request  [observed outcomes=returned:4 tests=4]
     └→ api.src.inference.model_manager.ModelManager._schedule_idle_unload_timer_locked  [observed outcomes=returned:6 tests=4]  (see above)

# api.src.inference.model_manager.ModelManager.generate  [origin=repo executed_by=4 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.tests.test_model_unload.test_active_request_blocks_idle_unload →  [observed outcomes=returned:4 tests=1]
  ├api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none →  [observed outcomes=returned:4 tests=1]
  ├api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled →  [observed outcomes=returned:4 tests=1]
  └api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  ├→ api.src.inference.model_manager.ModelManager.ensure_backend  [observed outcomes=returned:10 tests=4]
  │  ├⇢ api.src.inference.model_manager.ModelManager.initialize  [composed join=value rule=claim-member outcomes=returned:1 tests=3 probe-derived]  (see above)
  │  ├⇢ api.src.inference.model_manager.ModelManager.load_model  [composed join=value rule=claim-member outcomes=returned:3 tests=6 probe-derived]  (see above)
  │  ├→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=3 probe-derived]  (see above)
  │  ├→ api.src.inference.model_manager.ModelManager.initialize  [observed outcomes=returned:1 tests=1 probe-derived]  (see above)
  │  ├→ [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_initialize  [unresolved_boundary rule=no-claim tests=1]  (see above)
  │  ├→ [unresolved] py:api.tests.test_model_unload.test_ensure_backend_serializes_concurrent_reloads.<locals>.fake_load  [unresolved_boundary rule=no-claim tests=1]  (see above)
  │  └→ [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_initialize  [unresolved_boundary rule=no-claim tests=1]  (see above)
  ├→ api.src.inference.model_manager.ModelManager.hold  [observed outcomes=returned:4 tests=4]
  │  ├→ api.src.inference.model_manager.ModelManager._begin_request  [observed outcomes=returned:4 tests=4]  (see above)
  │  └→ api.src.inference.model_manager.ModelManager._end_request  [observed outcomes=returned:4 tests=4]  (see above)
  ├→ [unresolved] py:api.tests.test_model_unload.test_active_request_blocks_idle_unload.<locals>.slow_generate  [unresolved_boundary rule=no-claim tests=1]
  ├→ [unresolved] py:api.tests.test_model_unload.test_generate_lazy_reinit_when_backend_none.<locals>.fake_generate  [unresolved_boundary rule=no-claim tests=1]
  ├→ [unresolved] py:api.tests.test_model_unload.test_generate_schedules_idle_unload_when_enabled.<locals>.fake_generate  [unresolved_boundary rule=no-claim tests=1]
  └→ [unresolved] py:api.tests.test_model_unload.test_generate_skips_reinit_when_backend_set.<locals>.fake_generate  [unresolved_boundary rule=no-claim tests=1]

# api.src.inference.model_manager.ModelManager.unload_all  [origin=unknown executed_by=0 outcomes={}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  (no observed or composed caller)
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager.unload  [origin=repo executed_by=4 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.tests.test_model_unload.test_unload_calls_cuda_empty_cache_when_available →  [observed outcomes=returned:4 tests=1]
  ├api.tests.test_model_unload.test_unload_clears_backend →  [observed outcomes=returned:4 tests=1]
  ├api.tests.test_model_unload.test_unload_skips_cuda_empty_cache_when_unavailable →  [observed outcomes=returned:4 tests=1]
  └api.tests.test_model_unload.test_unload_when_already_none_is_noop →  [observed outcomes=returned:4 tests=1]
## downstream (what continues from it)
  ├→ [external] torch.cuda.empty_cache  [external_boundary rule=claim-outside-repo tests=1]
  ├→ [external] torch.cuda.is_available  [external_boundary rule=claim-outside-repo tests=4]
  ├→ api.src.inference.model_manager.ModelManager._cancel_idle_unload_timer  [observed outcomes=returned:18 tests=4]
  └→ api.src.inference.model_manager.ModelManager._unload_backend_locked  [observed outcomes=returned:7 tests=4]
     ├→ [external] time.monotonic  [external_boundary rule=claim-outside-repo tests=1]  (see above)
     └→ [unresolved] py:unittest.mock.MagicMock.unload  [unresolved_boundary rule=no-claim tests=6]  (see above)

# api.src.inference.model_manager.ModelManager.reload  [origin=unknown executed_by=0 outcomes={}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  (no observed or composed caller)
## downstream (what continues from it)
  (no observed continuation)

# api.src.inference.model_manager.ModelManager.status  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.tests.test_model_unload.test_status_reports_model_lifecycle_state →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  ├→ [external] time.monotonic  [external_boundary rule=claim-outside-repo tests=1]
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_enabled  [observed outcomes=returned:11 tests=1]
  │  └→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=8]  (see above)
  ├→ api.src.inference.model_manager.ModelManager._auto_unload_timeout  [observed outcomes=returned:21 tests=1]
  └→ api.src.inference.model_manager.ModelManager.current_backend  [observed outcomes=returned:1 tests=1]

# api.src.routers.development.reload_model  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.tests.test_model_unload.test_reload_endpoint_returns_status →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  └→ [gap] api.src.services.tts_service.TTSService  [internal_gap rule=claim-member tests=1]

# api.src.routers.development.model_status  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.tests.test_model_unload.test_model_status_endpoint_returns_status →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  └→ [gap] api.src.services.tts_service.TTSService  [internal_gap rule=claim-member tests=1]

# api.src.services.tts_service.TTSService.generate_from_phonemes  [origin=repo executed_by=1 outcomes={'returned': 1}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  └api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code →  [observed outcomes=returned:1 tests=1]
## downstream (what continues from it)
  ├⇢ api.src.inference.kokoro_v1.KokoroV1._get_pipeline  [composed join=value +3 same-shape rule=claim-member outcomes=returned:6 tests=5 probe-derived]
  │  ├→ [external] kokoro.pipeline.KPipeline.__init__  [external_boundary rule=claim-outside-repo tests=3]
  │  └→ [unresolved] py:api.tests.test_diffgenome_probe_2_1.test_get_pipeline_executes_with_lang_code_and_caches.<locals>.DummyPipeline.__init__  [unresolved_boundary rule=no-claim tests=1 probe-derived]
  ├⇢ api.src.services.tts_service.TTSService.get_voices_path  [composed join=arg_shape +1 same-shape rule=claim-member outcomes=returned:3 tests=4]
  │  ├→ [external] tempfile.gettempdir  [external_boundary rule=claim-outside-repo tests=1]
  │  ├→ [external] torch.serialization.save  [external_boundary rule=claim-outside-repo tests=1]
  │  ├→ api.src.services.tts_service.TTSService._load_voice_from_path  [observed outcomes=returned:2 tests=1]
  │  │  └→ [external] torch.serialization.load  [external_boundary rule=claim-outside-repo tests=1]
  │  └→ [unresolved] api.src.inference.voice_manager.get_manager.().get_voice_path  [unresolved_boundary rule=claim-return-chain tests=3]
  ├→ [unresolved] api.src.inference.kokoro_v1.KokoroV1._get_pipeline.().generate_from_tokens  [unresolved_boundary rule=claim-return-chain tests=1]
  ├→ [unresolved] api.src.inference.model_manager.get_manager.().ensure_backend  [unresolved_boundary rule=claim-return-chain tests=1]
  ├→ [unresolved] api.src.inference.model_manager.get_manager.().get_backend  [unresolved_boundary rule=claim-return-chain tests=1]
  ├→ [unresolved] api.src.inference.model_manager.get_manager.().hold  [unresolved_boundary rule=claim-return-chain tests=1]
  └→ [unresolved] py:api.tests.test_tts_service.test_generate_from_phonemes_uses_default_voice_code.<locals>.noop_hold  [unresolved_boundary rule=no-claim tests=1]
