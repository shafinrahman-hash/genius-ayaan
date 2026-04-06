#!/bin/sh
# Single-container: Ollama + Streamlit. Ollama listens on 127.0.0.1:11434; the app uses OLLAMA_BASE_URL.
set -e

export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
HOST_URL="http://127.0.0.1:11434"

echo "[genius-ayaan] Starting Ollama (OLLAMA_HOST=${OLLAMA_HOST})..."
ollama serve &
i=0
while [ "$i" -lt 180 ]; do
  if curl -sf "${HOST_URL}/api/tags" >/dev/null 2>&1; then
    echo "[genius-ayaan] Ollama is responding."
    break
  fi
  i=$((i + 1))
  sleep 1
done
if [ "$i" -ge 180 ]; then
  echo "[genius-ayaan] ERROR: Ollama did not become ready at ${HOST_URL}"
  exit 1
fi

if [ -n "${OLLAMA_MODELS:-}" ]; then
  MODEL_LIST="$OLLAMA_MODELS"
else
  MODEL_LIST="${OLLAMA_MODEL:-llama3.2}"
fi

# Pull in background so Streamlit binds quickly (first pull can take many minutes).
(
  for MODEL in $(echo "$MODEL_LIST" | tr ',' '\n'); do
    MODEL=$(echo "$MODEL" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -z "$MODEL" ] && continue
    echo "[genius-ayaan] Pulling model in background: ${MODEL}"
    ollama pull "$MODEL" || echo "[genius-ayaan] Warning: ollama pull failed for ${MODEL}"
  done
) &

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
echo "[genius-ayaan] OLLAMA_BASE_URL=${OLLAMA_BASE_URL} — starting Streamlit on port ${PORT:-8501}"

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-8501}" \
  --server.headless true \
  --browser.gatherUsageStats=false
