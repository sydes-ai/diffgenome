# diffgenome

**Runtime evidence for code changes.** diffgenome runs a repository's *existing* tests against a
change, records what actually executes, and reports it as a small, versioned JSON contract
(`diffgenome-runtime/1`) that a reviewer or a review tool can consume.

It answers questions static analysis and models can only guess at:

- Which changed functions did the existing tests actually execute, and in **exactly which tests
  and subtests**?
- Through which call chains did execution reach the changed code, including dynamic dispatch,
  registries and decorators the static call graph cannot follow?
- Which **outcomes** of each changed condition were observed (true / false / never evaluated)?
- How did the changed code exit (returned, returned-error, raised `<type>`), and with which
  argument type shapes?
- Where did observation stop: mocks, fakes, eager task runners, external systems?
- Which changed behavior did **no existing test exercise**?

No model is involved. Everything reported was observed, or is a static decision site needed to
place an observed outcome on a changed line.

## Install

```bash
pip install diffgenome
```

Python 3.12+ (the Python tracer uses `sys.monitoring`; the target's own interpreter too). No runtime dependencies. Language
support:

| target | tests run with | needs |
|---|---|---|
| Python | pytest | the target's virtualenv (`--python`) |
| Go | `go test` | a Go 1.22+ toolchain (it also builds the instrumenter; older modules are fine) with the module's dependencies downloaded (`go mod download`); tests run offline |
| Node / TypeScript | Jest | the target's `node_modules` (TypeScript is taken from there, or from `DIFFGENOME_NODE_PATH`) |

Tests run inside a disposable copy of the repository (never the checkout itself), under an
OS sandbox chosen per platform:

| host | sandbox | needs |
|---|---|---|
| macOS | `sandbox-exec` (Seatbelt) | nothing extra |
| Linux | `bwrap` (bubblewrap: user, network, PID and mount namespaces) | `bubblewrap` installed and unprivileged user namespaces allowed. Ubuntu 24.04 restricts them: `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` (GitHub-hosted runners allow this) |

Either way: no network beyond the sandbox, writes only inside the workspace, a scrubbed
environment, and child processes stay confined. `--allow-loopback` lets tests use localhost
servers they start themselves; on macOS it also reaches services on the host's loopback (a
local database), on Linux it does not. Without a usable sandbox diffgenome refuses to run
target tests and says why.

## Use

```bash
# Python: the change between two revisions, the tests that cover it
diffgenome change --runtime python --repo . --python .venv/bin/python \
  --source-root src --test-root tests --diff main..HEAD --out .diffgenome/run

# Go
diffgenome change --runtime go --repo . --test-root api --tests ./api/ \
  --mock-dir db/mock --diff main..HEAD --out .diffgenome/run

# analyze a revision other than the checkout, without touching the checkout
diffgenome change ... --rev <head> --diff <base>..<head>
```

Python traces keep only what bears on the change: calls to changed functions, every frame
above them back to the test, and `--down` levels below them. Unrelated work in a test (fixture
setup, bulk data) is dropped as the test finishes, so large suites stay affordable. Use
`--full-traces` to keep every call.

The result is `.diffgenome/run/diffgenome-change.json`. Its `runtime` section is the contract:

```jsonc
{
  "format": "diffgenome-runtime/1",
  "universe": { "test_scope": "tests/", "executions": 55, "passed": 55, "failed": 0, "tests": [...] },
  "changed_functions": [{
    "symbol": "py:app.rows.handler.RowHandler.restore_row", "file": "...", "line": 3221, "origin": "repo",
    "executed": true, "calls": 3, "tests": ["...::test_editor_can_redo_create_row", "..."],
    "exits": { "returned": 3 }, "raised_inside": {}, "arg_shapes": [[["user", "User"], ["row_id", "int"]]],
    "callers": [{ "symbol": "...DeleteRowActionType.undo", "calls": 2, "tests": 2 }],
    "stand_ins": {},
    "changed_sites": [{ "line": 3240, "predicate": "view is None", "true": 0, "false": 3 }]
  }],
  "edges": [{ "caller": {...}, "callee": {...}, "executions": 2, "tests": [...], "tests_total": 2 }],
  "boundaries": [{ "kind": "external", "caller": "...", "target": "celery.canvas._chord" }],
  "gaps": [
    { "kind": "function_not_executed", "symbol": "...TrashHandler.restore_item" },
    { "kind": "branch_outcome_not_observed", "line": 217, "predicate": "not fields", "outcome": "true" },
    { "kind": "stand_in_reached", "target": "...FormulaFieldType.run_periodic_update" }
  ],
  "not_reported": ["values (only type shapes and opaque fingerprints are recorded)",
                   "except-handler coverage (handlers are not decision sites)", "per-line coverage"]
}
```

Every "not executed" is relative to `universe.test_scope`: the tests that were run. Locations
carry `origin` (`repo`, `test`, `external`) so a consumer can tell application frames from test
frames.

A caller is the innermost instrumented frame active when the callee was entered, which does not
by itself prove a direct call. An edge or caller may carry `relation` only when its relationship
was positively classified (a missing `relation` is unspecified): `through_external` with a
`via` naming the external call it ran inside, e.g. `CommandBus.execute` with argument shape
`DeleteUserCommand` (Node, behind the experimental `DIFFGENOME_EXTERNAL_BRIDGES=1`). See
[docs/integration-artifact.md](docs/integration-artifact.md).

The artifact's other sections (`nodes`, `edges`, `executions`, `boundaries`, `facts`) describe
the observed behavioral neighborhood of the change; `report.md` and `behavioral-map.md` render
it for people.

## Consumers

[Sydes](https://pypi.org/project/sydes/) uses the runtime contract for change verification:
observed call edges join its call graph for reachability, the exact tests per changed function
become supporting test evidence, the gaps become verification gaps, and AI recovery is only asked
about what the runtime evidence cannot answer. Sydes depends on the contract alone, not on
diffgenome internals.

## Optional: the Behavioral Genome (research)

`diffgenome genome` builds a semantic layer on top of the runtime evidence: a model proposes
behavioral rules (variables, decisions, transitions), and a deterministic checker keeps only the
rules the observed executions verify or support. It is optional research code: nothing in
`diffgenome change` or the runtime contract uses it, and it needs no extra packages (an OpenAI
key only for live proposals, read from `OPENAI_API_KEY` or `~/.config/diffgenome/openai_api_key`).
Install with `pip install "diffgenome[genome]"` to state the intent. See
`docs/research-overview.md` and `docs/runtime-evaluation.md` for what has and has not been
shown to work.

## Versions

Use **0.1.8 or later**. 0.1.4 and 0.1.5 are broken (0.1.4 skipped pytest configs in
subdirectories; 0.1.5 failed every project with `filterwarnings = error`) and should be
yanked. 0.1.6 crashed on tests whose threads outlive them. 0.1.7 reported and traced only
the first `--source-root`, so changes in other packages of a workspace were silently
missing. `--source-root`, `--test-root` and `--pythonpath` are repeatable.

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests ci && uv run mypy src
```

Without a usable sandbox the sandboxed tests skip locally. Set `DIFFGENOME_REQUIRE_SANDBOX=1`
to make that a failure, as CI does.

CI is layered:

- `.github/workflows/ci.yml`, on every push and pull request: the full suite on
  ubuntu-latest (bubblewrap) and macos-15 (Seatbelt) × Python 3.12 and 3.13, with the
  sandbox required. That includes the sandbox invariants (`tests/test_sandbox_invariants.py`)
  and the layout and regression fixtures (`tests/test_layouts.py`): package at the root, src
  layout, per-app Django-style tests, uv workspace, tests inside the package, single module,
  subdirectory pytest config, `filterwarnings = error`, threads outliving their test,
  import-time execution, an unimportable test file. A `package` job builds the wheel and
  installs it into a clean virtualenv.
- `.github/workflows/smoke.yml`, on main, release tags and on demand: real repositories at
  pinned commits (`ci/smoke-cases.json`: healthchecks, requests, tomlkit, itsdangerous,
  toolz, demo-orders-api), run zero-config through Sydes with the wheel built from this
  commit, on Linux and macOS. `ci/smoke_assert.py` checks minimum facts per case (tests
  passed, named changed functions executed, import-time execution).

Release: bump `version` in `pyproject.toml` and `__version__` in `src/diffgenome/__init__.py`,
check that both workflows pass on main, then `uv build && uv publish`, then tag `vX.Y.Z` (that
tag runs the smoke matrix once more).

## License

Apache-2.0. See [LICENSE](LICENSE).
