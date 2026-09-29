<!-- sydes-verification-comment -->

## Sydes

**◐ Analysis complete** · Medium impact

### Change

Behavior changes related to rate and voice tags in text processing and testing.

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

### Test evidence

| Check | Result |
| --- | --- |
| Relevant regression test | ✅ Found |
| API behavior | 🟡 Exercised, not asserted |
| Validation behavior | 🟡 Found, not executed |
| Test executed by Sydes | ⬛ Not run (`--no-run-tests`) |
| Route coverage | 🟡 Incomplete |

_Route composition is unresolved in kokoro; some routes may be missing._

| Test | Route | Checks the behavior | Run by Sydes |
| --- | --- | --- | --- |
| `test_openai_endpoints.py::test_openai_voice_mapping` | POST /v1/audio/speech | No | No |
| `test_openai_endpoints.py::test_openai_voice_mapping_streaming` | POST /v1/audio/speech | No | No |
| `test_openai_endpoints.py::test_invalid_openai_model` | POST /v1/audio/speech | No | No |
| `test_openai_endpoints.py::test_openai_speech_streaming` | POST /v1/audio/speech | No | No |

_…and 55 more mapped test(s) in the full result._

### Code review

**Blocking issue(s) found**

- Possible data corruption due to inconsistent rate and voice tag handling. (api/src/routers/openai_compatible.py:211)

<details><summary>Technical evidence</summary>

- **Changed symbols:** `process_and_validate_voice_tags`, `split_by_voice`

</details>

---
Sydes
