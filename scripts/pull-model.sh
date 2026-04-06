#!/bin/sh
# Waits for Ollama, then pulls OLLAMA_MODEL if missing (via HTTP API).
# Used by the ollama-pull service so deploys do not need manual `docker exec`.

set -e
HOST="${OLLAMA_HOST:-http://ollama:11434}"
# Comma-separated list, e.g. OLLAMA_MODELS=llama3.2,qwen2.5-coder:7b
# If unset, uses OLLAMA_MODEL once (backward compatible).
if [ -n "${OLLAMA_MODELS:-}" ]; then
  MODEL_LIST="$OLLAMA_MODELS"
else
  MODEL_LIST="${OLLAMA_MODEL:-llama3.2}"
fi

echo "Waiting for Ollama at ${HOST}..."
i=0
while [ "$i" -lt 120 ]; do
  if curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
    echo "Ollama is ready."
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$i" -eq 120 ]; then
  echo "ERROR: Ollama did not become ready in time."
  exit 1
fi

TAGS=$(curl -sf "${HOST}/api/tags") || exit 1

pull_if_missing() {
  MODEL="$1"
  [ -z "$MODEL" ] && return 0
  if echo "$TAGS" | grep -q "\"name\":\"${MODEL}\""; then
    echo "Model '${MODEL}' is already available — skipping."
    return 0
  fi
  echo "Pulling '${MODEL}' (first deploy can take several minutes)..."
  curl -sS -X POST "${HOST}/api/pull" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${MODEL}\"}" \
    -o /dev/null
  echo "Pull finished for '${MODEL}'."
}

for MODEL in $(echo "$MODEL_LIST" | tr ',' '\n'); do
  MODEL=$(echo "$MODEL" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [ -z "$MODEL" ] && continue
  pull_if_missing "$MODEL"
  TAGS=$(curl -sf "${HOST}/api/tags") || exit 1
done
