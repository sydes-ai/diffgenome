#!/bin/bash
# run.sh <name> <clone> <artifact> : Sydes static-only (S) then static+runtime (R), one run each
set -u
S=/private/tmp/claude-501/-Users-ksnaik-StudioProjects-diffgenome/aefb02de-a379-42cc-819b-9d59916c2d04/scratchpad
n=$1 CLONE=$2 ART=$3
BASE=$(git -C $CLONE rev-parse HEAD^)
[ "$n" = pr103 ] && BASE=6e2679863e4c691db46ec14761a3b3e303e05ce1
export SYDES_CODE_INTELLIGENCE=cbm SYDES_CBM_EXECUTABLE=$HOME/.local/bin/codebase-memory-mcp
export OPENAI_API_KEY="$(cat $HOME/.config/diffgenome/openai_api_key)"
export SYDES_LLM_PROVIDER=openai SYDES_LLM_MODEL=gpt-6-astra SYDES_LLM_REASONING_EFFORT=xhigh
export SYDES_LLM_TEMPERATURE=default SYDES_LLM_TIMEOUT_SECONDS=1800 SYDES_LLM_CONTEXT_CHARS=120000
SY=$HOME/StudioProjects/sydes/.venv/bin/sydes
for cfg in S R; do
  D=$S/rt/$n/$cfg; rm -rf $D; mkdir -p $D/trace
  extra=""; [ $cfg = R ] && extra="--behavioral-map diffgenome --behavioral-artifact $ART --behavioral-context on"
  t0=$(date +%s)
  SYDES_TRACE_DIR=$D/trace $SY verify-change --base $BASE --repo app=$CLONE --model openai:gpt-6-astra \
    --llm-policy auto --impact-guide auto --no-run-tests $extra \
    --json $D/sydes-result.json > $D/terminal.txt 2> $D/stderr.txt
  echo "$(( $(date +%s) - t0 ))" > $D/seconds.txt
done
echo "$n done"
