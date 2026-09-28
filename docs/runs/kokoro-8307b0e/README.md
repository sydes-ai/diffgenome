# Run record: Kokoro-FastAPI, commit 8307b0e (model auto-unload)

Target: `~/sample_repos/Kokoro-FastAPI` at `5152e8b` (read-only), change `8307b0e^..8307b0e`.
Date: 2026-09-28. Model: `gpt-5` via the OpenAI chat completions API.

- `report.md`: the definitive run. Existing tests traced under confinement, then the
  three gpt-5 probe drafts replayed through the recorded writer (deterministic, no tokens)
  after the collector fix described in `docs/experiment-03.md`.
- `report-live-first-pass.md`: the live run that produced the drafts. Same probes, one
  collector inconsistency (a patched class claimed the class rather than its `__init__`),
  hence one gap more in its "after" column.
- `probes/probe-{0,1,2}.py`: the generated probes, verbatim. They were written to a
  disposable workspace copy only and executed under Seatbelt with no network.

Command:

```bash
uv run python -m diffgenome mvp --repo ~/sample_repos/Kokoro-FastAPI --python .venv/bin/python \
  --test-root api/tests --diff 8307b0e --pytest-arg="--no-cov --ignore=api/tests/integration" \
  --writer openai --probes 3 --attempts 2 --out out/kokoro-8307b0e
```
