legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  → [unresolved] stand-in not resolved  → [external] outside the repository  → [os] kernel boundary

# api.src.routers.openai_compatible._load_core_json  [origin=repo executed_by=3 outcomes={'returned': 4}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.routers.openai_compatible.load_voice_grades ⇢  [composed join=value +2 same-shape rule=claim-member outcomes=returned:4 tests=3 probe-derived]
  │  ├api.src.routers.openai_compatible.<module>@1 →  [observed outcomes=returned:2 tests=1 probe-derived]
  │  │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:2 tests=1 probe-derived]
  ├api.src.routers.openai_compatible.load_openai_mappings →  [observed outcomes=returned:4 tests=3 probe-derived]
  │  ├api.src.routers.openai_compatible.<module>@1 →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:1 tests=1 probe-derived]
  │  ├api.tests.test_openai_endpoints.test_load_openai_mappings →  [observed outcomes=returned:3 tests=1]
  │  └api.tests.test_openai_endpoints.test_load_openai_mappings_file_not_found →  [observed outcomes=returned:3 tests=1]
  └api.src.routers.openai_compatible.load_voice_grades →  [observed outcomes=returned:4 tests=1 probe-derived]
     ├api.src.routers.openai_compatible.<module>@1 →  [observed outcomes=returned:2 tests=1 probe-derived]
     │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:1 tests=1 probe-derived]
     └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:2 tests=1 probe-derived]
## downstream (what continues from it)
  └→ [external] posixpath.join  [external_boundary rule=claim-outside-repo tests=2]

# api.src.routers.openai_compatible.load_openai_mappings  [origin=repo executed_by=3 outcomes={'returned': 3}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.routers.openai_compatible.<module>@1 →  [observed outcomes=returned:3 tests=1 probe-derived]
  │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:1 tests=1 probe-derived]
  ├api.tests.test_openai_endpoints.test_load_openai_mappings →  [observed outcomes=returned:3 tests=1]
  └api.tests.test_openai_endpoints.test_load_openai_mappings_file_not_found →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  └→ api.src.routers.openai_compatible._load_core_json  [observed outcomes=returned:4 tests=3 probe-derived]
     └→ [external] posixpath.join  [external_boundary rule=claim-outside-repo tests=2]  (see above)

# api.src.routers.openai_compatible.load_voice_grades  [origin=repo executed_by=1 outcomes={'returned': 2}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.src.routers.openai_compatible.<module>@1 →  [observed outcomes=returned:2 tests=1 probe-derived]
  │  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:1 tests=1 probe-derived]
  └api.tests.test_diffgenome_probe_0_1.test_probe_load_voice_grades_calls_core_loader_and_returns_result →  [observed outcomes=returned:2 tests=1 probe-derived]
## downstream (what continues from it)
  ├⇢ api.src.routers.openai_compatible._load_core_json  [composed join=value +2 same-shape rule=claim-member outcomes=returned:4 tests=3 probe-derived]
  │  └→ [external] posixpath.join  [external_boundary rule=claim-outside-repo tests=2]  (see above)
  └→ api.src.routers.openai_compatible._load_core_json  [observed outcomes=returned:4 tests=1 probe-derived]
     └→ [external] posixpath.join  [external_boundary rule=claim-outside-repo tests=2]  (see above)

# api.src.routers.openai_compatible.list_voices  [origin=repo executed_by=2 outcomes={'returned': 3}]
## upstream (who reaches it; each line is `caller →/⇢ this`)
  ├api.tests.test_openai_endpoints.test_list_voices →  [observed outcomes=returned:3 tests=1]
  └api.tests.test_openai_endpoints.test_list_voices_grades →  [observed outcomes=returned:3 tests=1]
## downstream (what continues from it)
  ├⇢ api.src.routers.openai_compatible.get_tts_service  [composed join=value +9 same-shape rule=claim-member outcomes=returned:5 tests=3]
  │  └⇢ api.src.services.tts_service.TTSService.create  [composed join=value +24 same-shape rule=claim-member outcomes=returned:27 tests=26]
  │     ├⇢ api.src.inference.model_manager.get_manager  [composed join=symbol +114 same-shape rule=claim-member outcomes=returned:8 tests=25]
  │     │  └→ api.src.inference.model_manager.ModelManager.__init__  [observed outcomes=returned:15 tests=1]
  │     ├⇢ api.src.inference.voice_manager.get_manager  [composed join=value +114 same-shape rule=claim-member outcomes=returned:8 tests=25]
  │     │  └→ api.src.inference.voice_manager.VoiceManager.__init__  [observed outcomes=returned:1 tests=1]
  │     ├→ api.src.inference.model_manager.get_manager  [observed outcomes=returned:8 tests=6]
  │     │  └→ api.src.inference.model_manager.ModelManager.__init__  [observed outcomes=returned:15 tests=1]  (see above)
  │     ├→ api.src.inference.voice_manager.get_manager  [observed outcomes=returned:8 tests=6]
  │     │  └→ api.src.inference.voice_manager.VoiceManager.__init__  [observed outcomes=returned:1 tests=1]  (see above)
  │     └→ api.src.services.tts_service.TTSService.__init__  [observed outcomes=returned:27 tests=25]
  └⇢ api.src.services.tts_service.TTSService.list_voices  [composed join=value rule=static-return-type outcomes=returned:1 tests=3]
     └→ [gap] api.src.inference.voice_manager.VoiceManager.list_voices  [internal_gap rule=static-return-type tests=1]
