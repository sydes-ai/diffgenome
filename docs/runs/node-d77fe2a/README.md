# Run record: express-typescript-boilerplate, commit d77fe2a (reject non-positive pet ages)

Target: `~/sample_repos/express-typescript-boilerplate` at `69a9091` (read-only), Node v22.19.0,
Jest 23.6, change `d77fe2a^..d77fe2a`. Date: 2026-09-28. Model: `gpt-5`. See `docs/experiment-04.md`.

- `empirical-summary.txt`: existing tests under the Node collector (13 tests).
- `report.md`, `map.md`, `graph.json` / `graph-before.json`: the change-centred run with one
  accepted probe; query with `python -m diffgenome inspect --graph graph.json --symbol PetService.create`.
- `probes/`: the rejected and accepted gpt-5 drafts verbatim, and the rejected attempt's log.

Command:

```bash
uv run python -m diffgenome mvp --runtime node --repo ~/sample_repos/express-typescript-boilerplate \
  --source-root src --test-root test/unit --diff d77fe2a --writer openai --probes 2 --attempts 2 --out out/node
```
