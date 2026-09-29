legend: → observed continuation  ⇢ composed continuation (grade)  [external] outside the repo  [unresolved] stand-in without a resolution  [gap] internal continuation nobody has executed  [declaration] construction/declaration with no in-repo executable body

# api.src.routers.openai_compatible.process_and_validate_voice_tags   [changed; outcomes={'returned': 31, 'raised': 4}; reached by: tests 35: api/tests/test_openai_endpoints.py::test_alias_names_are_matched_regardless_of_case, api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag, api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input …]
## reaches the change
  ├api.src.routers.development.create_captioned_speech  [entrypoint] → this
  │     evidence: observed 2 exec · tests 2
  │     reached by: tests 6: api/tests/test_openai_endpoints.py::test_captioned_endpoint_403_when_voice_tags_disabled, api/tests/test_openai_endpoints.py::test_captioned_endpoint_translates_ssml_input, api/tests/test_openai_endpoints.py::test_captioned_ssml_without_voice_tags_is_rejected …
  └api.src.routers.openai_compatible.create_speech → this
        evidence: observed 22 exec · tests 22
     └api.src.routers.development.create_dialogue  [entrypoint] → this
           evidence: observed 5 exec · tests 5
           reached by: tests 6: api/tests/test_openai_endpoints.py::test_dialogue_endpoint, api/tests/test_openai_endpoints.py::test_dialogue_endpoint_403_when_voice_tags_disabled, api/tests/test_openai_endpoints.py::test_dialogue_endpoint_accepts_elevenlabs_field_names …
## continues from the change
  ├→ api.src.routers.openai_compatible.alias_rate
  │     evidence: observed 12 exec · tests 12
  │  └→ api.src.routers.openai_compatible._alias_target
  │        evidence: observed 31 exec · tests 31
  ├→ api.src.routers.openai_compatible.process_and_validate_voice_tags.<locals>.<lambda>@237
  │     evidence: observed 12 exec · tests 12
  ├→ api.src.routers.openai_compatible.process_and_validate_voices
  │     evidence: observed 16 exec · tests 16
  │  ├→ api.src.routers.openai_compatible.resolve_voice_alias
  │  │     evidence: observed 41 exec · tests 41
  │  │  └→ api.src.routers.openai_compatible._alias_target
  │  │        evidence: observed 42 exec · tests 42
  │  └⇢ api.src.services.tts_service.TTSService.list_voices (VALUE)
  │        evidence: composed VALUE x41 · rule=claim-member/static-return-type · tests 33
  │     └→ [gap] api.src.inference.voice_manager.VoiceManager.list_voices
  │           evidence: rule=static-return-type · tests 1
  └⇢ api.src.services.tts_service.TTSService.list_voices (VALUE)
        evidence: composed VALUE x16 · rule=claim-member/static-return-type · tests 17
     └→ [gap] api.src.inference.voice_manager.VoiceManager.list_voices  (see above)

# api.src.services.text_processing.text_processor.split_by_voice   [changed; outcomes={'returned': 24}; reached by: tests 23: api/tests/test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag, api/tests/test_openai_endpoints.py::test_rate_tag_scales_the_alias_base_rate, api/tests/test_text_processor.py::test_baserate_persists_across_voice_change …]
## reaches the change
  └api.src.services.tts_service.TTSService._split_multi_voice → this
        evidence: observed 7 exec · tests 7
     └api.src.services.tts_service.TTSService.generate_audio_stream → this
           evidence: observed 6 exec · tests 6
        └api.src.services.tts_service.TTSService.generate_audio → this
              evidence: observed 1 exec · tests 1
           └api.src.routers.openai_compatible.create_speech ⇢ (ARG_SHAPE) this
                 evidence: composed ARG_SHAPE x10 · rule=static-return-type · tests 11
              └api.src.routers.development.create_dialogue  [entrypoint] → this
                    evidence: observed 5 exec · tests 5
                    reached by: tests 6: api/tests/test_openai_endpoints.py::test_dialogue_endpoint, api/tests/test_openai_endpoints.py::test_dialogue_endpoint_403_when_voice_tags_disabled, api/tests/test_openai_endpoints.py::test_dialogue_endpoint_accepts_elevenlabs_field_names …
## continues from the change
  └→ api.src.structures.schemas.clamp_rate
        evidence: observed 19 exec · tests 19

