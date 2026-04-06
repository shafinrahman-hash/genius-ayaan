# Ollama + Streamlit in one container (default for Render and `docker compose up`).
# Needs enough RAM for your model (e.g. several GB for llama3.2-class weights).

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl zstd \
  && rm -rf /var/lib/apt/lists/*

# Official install — provides `ollama` binary and server
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py model_router.py .
COPY assets ./assets
COPY .streamlit ./.streamlit
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["/docker-entrypoint.sh"]
