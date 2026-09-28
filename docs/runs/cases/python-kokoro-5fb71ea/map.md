legend: → observed continuation  ⇢ composed continuation (grade)  [external] outside the repo  [unresolved] stand-in without a resolution  [gap] internal continuation nobody has executed  [declaration] construction/declaration with no in-repo executable body

# api.src.routers.openai_compatible._load_core_json   [changed; outcomes={'returned': 4}; reached by: tests 2: api/tests/test_openai_endpoints.py::test_load_openai_mappings, api/tests/test_openai_endpoints.py::test_load_openai_mappings_file_not_found; probes 1]
## reaches the change
  ├api.src.routers.openai_compatible.load_openai_mappings → this
  │     evidence: observed 3 exec · tests 2 · probes 1
  │  └api.src.routers.openai_compatible.<module>@1  [entrypoint] → this
  │        evidence: observed 1 exec · tests 0 · probes 1
  │        reached by: probes 1
  └api.src.routers.openai_compatible.load_voice_grades → this
        evidence: observed 1 exec · composed VALUE x1 · composed ARG_SHAPE x1 · +2 same-shape · AMBIGUOUS · rule=claim-member · tests 2 · probes 1
     └api.src.routers.openai_compatible.<module>@1  [entrypoint] → this
           evidence: observed 1 exec · tests 0 · probes 1
           reached by: probes 1
## continues from the change
  └→ [external] posixpath.join
        evidence: rule=claim-outside-repo · tests 2

# api.src.routers.openai_compatible.load_openai_mappings   [changed; outcomes={'returned': 3}; reached by: tests 2: api/tests/test_openai_endpoints.py::test_load_openai_mappings, api/tests/test_openai_endpoints.py::test_load_openai_mappings_file_not_found; probes 1]
## reaches the change
  └api.src.routers.openai_compatible.<module>@1  [entrypoint] → this
        evidence: observed 1 exec · tests 0 · probes 1
        reached by: probes 1
## continues from the change
  └→ api.src.routers.openai_compatible._load_core_json
        evidence: observed 3 exec · tests 2 · probes 1
     └→ [external] posixpath.join  (see above)

# api.src.routers.openai_compatible.load_voice_grades   [changed; outcomes={'returned': 2}; reached by: probes 1]
## reaches the change
  └api.src.routers.openai_compatible.<module>@1  [entrypoint] → this
        evidence: observed 1 exec · tests 0 · probes 1
        reached by: probes 1
## continues from the change
  └→ api.src.routers.openai_compatible._load_core_json
        evidence: observed 1 exec · composed VALUE x1 · composed ARG_SHAPE x1 · +2 same-shape · AMBIGUOUS · rule=claim-member · tests 2 · probes 1
     └→ [external] posixpath.join  (see above)

# api.src.routers.openai_compatible.list_voices   [changed; outcomes={'returned': 3}; reached by: tests 2: api/tests/test_openai_endpoints.py::test_list_voices, api/tests/test_openai_endpoints.py::test_list_voices_grades]
## reaches the change
  (no production caller observed or composed; only tests/probes call it directly)
## continues from the change
  ├⇢ api.src.routers.openai_compatible.get_tts_service (VALUE)
  │     evidence: composed VALUE x6 · +9 same-shape · AMBIGUOUS · rule=claim-member · tests 3
  │  └⇢ api.src.services.tts_service.TTSService.create (VALUE)
  │        evidence: composed VALUE x3 · +24 same-shape · AMBIGUOUS · rule=claim-member · tests 26
  │     ├→ api.src.inference.model_manager.get_manager
  │     │     evidence: observed 6 exec · composed SYMBOL x38 · +114 same-shape · AMBIGUOUS · rule=claim-member · tests 25
  │     │  └→ api.src.inference.model_manager.ModelManager.__init__
  │     │        evidence: observed 1 exec · tests 1
  │     ├→ api.src.inference.voice_manager.get_manager
  │     │     evidence: observed 6 exec · composed VALUE x38 · +114 same-shape · AMBIGUOUS · rule=claim-member · tests 25
  │     │  └→ api.src.inference.voice_manager.VoiceManager.__init__
  │     │        evidence: observed 1 exec · tests 1
  │     └→ api.src.services.tts_service.TTSService.__init__
  │           evidence: observed 25 exec · tests 25
  └⇢ api.src.services.tts_service.TTSService.list_voices (VALUE)
        evidence: composed VALUE x3 · rule=static-return-type · tests 3
     └→ [gap] api.src.inference.voice_manager.VoiceManager.list_voices
           evidence: rule=static-return-type · tests 1

