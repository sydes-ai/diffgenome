#!/bin/bash
# Experiment 10, case A: Baserow #6069 (fork: sydes-examples/baserow#1), exact refs.
#   usage: run_baserow_6069.sh head <out-dir> <venv-python>
#          run_baserow_6069.sh base <out-dir> <venv-python> <base-worktree>
# head: `git archive` of the fix (70c81307) from the fork clone.
# base: a copy of a detached worktree at the merge base (e9ef2697) into which the head's new
# upstream test file has been copied unchanged (the before-phenotype; the change itself is
# never altered).
# Needs a disposable local PostgreSQL on 127.0.0.1:55432 (test values only).
set -euo pipefail
WHICH=$1; OUT=$2; PY=$3; BASETREE=${4:-}
H=70c81307d3b6b4951f82cac65cc7779462c026ac
MB=e9ef2697baf8d6967e254b468bf82483de121e68
NEW=backend/tests/baserow/core/snapshots/test_snapshot_array_formula_import.py
EXTRA="backend/tests/baserow/contrib/database/field/test_field_utils.py backend/tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies backend/tests/baserow/contrib/database/field/test_field_types.py::test_import_export_formula_field"
SRC=(--repo ~/sample_repos/baserow --rev "$H")
if [ "$WHICH" = base ]; then SRC=(--repo "$BASETREE"); fi
exec uv run diffgenome change --runtime python "${SRC[@]}" --diff "$MB..$H" \
  --python "$PY" --source-root backend/src --test-root backend/tests --tests "$NEW" \
  --pytest-arg="-p no:cacheprovider $EXTRA" \
  --pythonpath backend/src --pythonpath premium/backend/src --pythonpath enterprise/backend/src \
  --pythonpath backend/tests --pythonpath premium/backend/tests --pythonpath enterprise/backend/tests \
  --test-env DATABASE_HOST=127.0.0.1 --test-env DATABASE_PORT=55432 --test-env DATABASE_USER=baserow \
  --test-env DATABASE_PASSWORD=baserow --test-env DATABASE_NAME=baserow \
  --allow-loopback --out "$OUT"
