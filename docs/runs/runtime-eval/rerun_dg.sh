#!/bin/bash
# rerun_dg.sh <n> <head> <tests> [pytest args...] : fixed DiffGenome into new dir, then swap in
set -u
S=/private/tmp/claude-501/-Users-ksnaik-StudioProjects-diffgenome/aefb02de-a379-42cc-819b-9d59916c2d04/scratchpad/pr
n=$1 H=$2 T=$3; shift 3
P=$(git -C ~/sample_repos/baserow rev-parse $H^)
NEW=$S/new-pr$n; rm -rf $NEW
cd ~/StudioProjects/diffgenome
uv run diffgenome change --runtime python --repo ~/sample_repos/baserow --rev "$H" --diff "$P..$H" \
  --python $S/../bw-head/backend/.venv/bin/python --source-root backend/src --test-root backend/tests --tests "$T" \
  --pytest-arg="-p no:cacheprovider $1" ${2:+--pytest-arg="$2"} \
  --pythonpath backend/src --pythonpath premium/backend/src --pythonpath enterprise/backend/src \
  --pythonpath backend/tests --pythonpath premium/backend/tests --pythonpath enterprise/backend/tests \
  --test-env DATABASE_HOST=127.0.0.1 --test-env DATABASE_PORT=55432 --test-env DATABASE_USER=baserow \
  --test-env DATABASE_PASSWORD=baserow --test-env DATABASE_NAME=baserow \
  --allow-loopback --out $NEW > $S/new-pr$n.log 2>&1
if [ -f $NEW/diffgenome-change.json ]; then rm -rf $S/old-pr$n; mv $S/pr$n $S/old-pr$n && mv $NEW $S/pr$n && echo "pr$n swapped"; else echo "pr$n FAILED"; fi
