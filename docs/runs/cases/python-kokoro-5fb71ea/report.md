# diffgenome behavioral impact report

Change: git diff 5fb71ea
Changed symbols (5):
  api.src.routers.openai_compatible._load_core_json  executed by 2 test(s)
  api.src.routers.openai_compatible.load_openai_mappings  executed by 2 test(s)
  api.src.routers.openai_compatible.load_voice_grades  executed by 0 test(s)  ← no existing execution
  api.src.routers.openai_compatible.list_voices  executed by 2 test(s)
  api.tests.test_openai_endpoints.test_list_voices_grades  executed by 0 test(s)  ← no existing execution
Changed files with no mapped code symbol: CHANGELOG.md, api/src/core/voice_grades.json, web/src/components/VoiceSelector.js, web/src/services/VoiceService.js, web/styles/voices.css, web/tests/unit/index.test.mjs, web/tests/unit/voice-service.test.mjs

## Behavioral neighborhood (before probes)

### Upstream (what reaches the change)
  d1  api.src.routers.openai_compatible.load_openai_mappings → api.src.routers.openai_compatible._load_core_json  tests=2
  d1  api.tests.test_openai_endpoints.test_list_voices → api.src.routers.openai_compatible.list_voices  tests=1
  d1  api.tests.test_openai_endpoints.test_list_voices_grades → api.src.routers.openai_compatible.list_voices  tests=1
  d1  api.tests.test_openai_endpoints.test_load_openai_mappings → api.src.routers.openai_compatible.load_openai_mappings  tests=1
  d1  api.tests.test_openai_endpoints.test_load_openai_mappings_file_not_found → api.src.routers.openai_compatible.load_openai_mappings  tests=1

### Downstream (what continues from the change)
  d1  api.src.routers.openai_compatible._load_core_json → [external] posixpath.join  tests=2  rule=claim-outside-repo
  d1  api.src.routers.openai_compatible.list_voices ⇢ api.src.routers.openai_compatible.get_tts_service  tests=3  join=value  rule=claim-member
  d1  api.src.routers.openai_compatible.list_voices ⇢ api.src.services.tts_service.TTSService.list_voices  tests=3  join=value  rule=static-return-type
  d2  api.src.routers.openai_compatible.get_tts_service ⇢ api.src.services.tts_service.TTSService.create  tests=26  join=value  rule=claim-member
  d2  api.src.services.tts_service.TTSService.list_voices → [gap] api.src.inference.voice_manager.VoiceManager.list_voices  tests=1  rule=static-return-type
  d3  api.src.services.tts_service.TTSService.create → api.src.inference.model_manager.get_manager  tests=6
  d3  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member
  d3  api.src.services.tts_service.TTSService.create → api.src.inference.voice_manager.get_manager  tests=6
  d3  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.voice_manager.get_manager  tests=25  join=value  rule=claim-member
  d3  api.src.services.tts_service.TTSService.create → api.src.services.tts_service.TTSService.__init__  tests=25
  d4  api.src.inference.model_manager.get_manager → api.src.inference.model_manager.ModelManager.__init__  tests=1
  d4  api.src.inference.voice_manager.get_manager → api.src.inference.voice_manager.VoiceManager.__init__  tests=1

### Tests establishing these paths (44)
  api/tests/test_model_unload.py::test_active_request_blocks_idle_unload
  api/tests/test_model_unload.py::test_ensure_backend_serializes_concurrent_reloads
  api/tests/test_model_unload.py::test_generate_lazy_reinit_when_backend_none
  api/tests/test_model_unload.py::test_generate_schedules_idle_unload_when_enabled
  api/tests/test_model_unload.py::test_generate_skips_reinit_when_backend_set
  api/tests/test_model_unload.py::test_idle_auto_unload_log_includes_configured_timeout
  api/tests/test_model_unload.py::test_load_model_does_not_schedule_idle_unload_during_active_request
  api/tests/test_model_unload.py::test_load_model_schedules_idle_unload_when_enabled
  api/tests/test_model_unload.py::test_manager_init_creates_lock
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
  api/tests/test_openai_endpoints.py::test_list_voices
  api/tests/test_openai_endpoints.py::test_list_voices_grades
  api/tests/test_openai_endpoints.py::test_load_openai_mappings
  api/tests/test_openai_endpoints.py::test_load_openai_mappings_file_not_found
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
  api/tests/test_tts_service.py::test_split_multi_voice_resolves_each_speaker_once
  ... 4 more

## Where knowledge stops (before probes)
### internal_gap (1)
  d2  api.src.services.tts_service.TTSService.list_voices → [gap] api.src.inference.voice_manager.VoiceManager.list_voices  tests=1  rule=static-return-type
### external_boundary (1)
  d1  api.src.routers.openai_compatible._load_core_json → [external] posixpath.join  tests=2  rule=claim-outside-repo
### weak joins (1)
  d3  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member

## Generated probes
- objective: uncovered_symbol api.src.routers.openai_compatible.load_voice_grades (from api.src.routers.openai_compatible.load_voice_grades, d0)
  attempt 1: accepted  model=recorded
  learned 18 observed edge(s):
    + py:api.src.routers.openai_compatible.<module>@1 → py:api.src.routers.<module>@1 [returned]
    + py:api.src.routers.openai_compatible.<module>@1 → py:api.src.routers.openai_compatible.load_openai_mappings [returned]
    + py:api.src.routers.openai_compatible.<module>@1 → py:api.src.routers.openai_compatible.load_voice_grades [returned]
    + py:api.src.routers.openai_compatible.<module>@1 → py:api.src.routers.ssml.<module>@1 [returned]
    + py:api.src.routers.openai_compatible.load_openai_mappings → py:api.src.routers.openai_compatible._load_core_json [returned]
    + py:api.src.routers.openai_compatible.load_voice_grades → py:api.src.routers.openai_compatible._load_core_json [returned]
    + py:api.src.routers.ssml.<module>@1 → py:api.src.services.text_processing.ssml.<module>@1 [returned]
    + py:api.src.routers.ssml.<module>@1 → py:api.src.structures.text_schemas.<module>@1 [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.GenerateFromPhonemesRequest [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.PhonemeRequest [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.PhonemeResponse [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.SsmlCapabilities [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.SsmlRequest [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.SsmlResponse [returned]
    + py:api.src.structures.text_schemas.<module>@1 → py:api.src.structures.text_schemas.StitchOptions [returned]

## Before vs after
| metric | before | after |
|---|---|---|
| observed edges | 10 | 15 |
| composed edges | 5 | 6 |
| strong joins (VALUE+) | 4 | 5 |
| weak joins | 1 | 1 |
| internal gaps | 1 | 1 |
| unresolved boundaries | 0 | 0 |
| external boundaries | 1 | 1 |
| os boundaries | 0 | 0 |
| unsound attempts | 0 | 0 |
| probe-derived edges | 0 | 7 |
| symbols | 18 | 20 |
| tests | 44 | 45 |
| reconstructed / provisional denominator | 14/16 = 0.875 | 20/22 = 0.909 |

Denominator is provisional: observed + composed edges + internal gaps + unresolved
stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior
no execution has come near, and external/OS boundaries, which are terminal by design.

## Remaining after probes
### internal_gap (1)
  d2  api.src.services.tts_service.TTSService.list_voices → [gap] api.src.inference.voice_manager.VoiceManager.list_voices  tests=1  rule=static-return-type
### unresolved_boundary (0)
### weak joins (1)
  d3  api.src.services.tts_service.TTSService.create ⇢ api.src.inference.model_manager.get_manager  tests=25  join=symbol  rule=claim-member

## Notes
- 60 factory().member stand-ins resolved through declared return types (rule static-return-type)
- 1 changed symbol(s) have no existing execution at all: api.src.routers.openai_compatible.load_voice_grades

## Behavioral map around the changed symbols

```
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

```

The full repo-level graph with every edge's provenance is `graph.json` next to this report (`graph-before.json` is the state before probes). Query it with `python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.
