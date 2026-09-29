<!-- sydes-verification-comment -->

## Sydes

**◐ Analysis complete** · Medium impact

### What it may affect

**Established**

```text
POST /v1/audio/speech
  → create_speech
```

```text
POST /dev/captioned_speech
  → create_captioned_speech
```

### Behavioral effect

```text
Reaches the change (→ observed in tests, ⇢ reconstructed across a mock)
  development.create_captioned_speech → openai_compatible.process_and_validate_voice_tags (changed)
  development.create_dialogue → openai_compatible.create_speech ⇢ TTSService.generate_audio → TTSService.generate_audio_stream → TTSService._split_multi_voice → text_processor.split_by_voice (changed)
Continues from the change
  → openai_compatible.alias_rate    not in the static trace
  → <locals>.<lambda>@237    not in the static trace
  → openai_compatible.process_and_validate_voices    not in the static trace
    ⇢ TTSService.list_voices    reconstructed · VALUE
  ⇢ TTSService.list_voices    reconstructed · VALUE
  → schemas.clamp_rate    not in the static trace
Evidence stops
  TTSService.list_voices → VoiceManager.list_voices    gap: no test executes it
```

_How we know: 52 existing test(s) executed the changed code in isolation (`test_alias_rate_expands_to_a_baserate_tag` (changed in this diff), `test_baserate_persists_across_voice_change` (changed in this diff), `test_split_baserate_product_clamps_to_speed_bounds` (changed in this diff) and 49 more); existing tests only. Executing is not asserting: see Test evidence._

### Test evidence

| Check | Result |
| --- | --- |
| Relevant regression test | ✅ Found |
| API behavior | 🟡 Exercised, not asserted |
| Validation behavior | 🟡 Found, not executed |
| Test executed by Sydes | ⬛ Not run (`--no-run-tests`) |
| Executed in isolation (DiffGenome) | ✅ 52 test(s) ran the changed code |
| Route coverage | 🟡 Incomplete |

_PR semantic analysis unavailable: model output was not valid JSON._

| Test | Route | Checks the behavior | Run by Sydes |
| --- | --- | --- | --- |
| `test_openai_endpoints.py::test_alias_rate_expands_to_a_baserate_tag` | POST /v1/audio/speech | No | Yes, isolated (DiffGenome) |
| `test_text_processor.py::test_split_baserate_product_clamps_to_speed_bounds` | POST /v1/audio/speech | No | Yes, isolated (DiffGenome) |
| `test_text_processor.py::test_baserate_persists_across_voice_change` | POST /v1/audio/speech | No | Yes, isolated (DiffGenome) |
| `test_openai_endpoints.py::test_openai_voice_mapping` | POST /v1/audio/speech | No | Yes, isolated (DiffGenome) |

_…and 68 more mapped test(s) in the full result._

### Code review

**No blocking issues found**

<details><summary>Technical evidence</summary>

- **Changed symbols:** `process_and_validate_voice_tags`, `split_by_voice`
- **Behavioral evidence:** DiffGenome `diffgenome-change/1` · runtime `python/pytest` · observed 13 · reconstructed 3 · static steps executed 2/2

</details>

---
Sydes
