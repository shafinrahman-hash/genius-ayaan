FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py model_router.py .
COPY assets ./assets
COPY .streamlit ./.streamlit

EXPOSE 8501

# Render (and similar hosts) set PORT; default 8501 for local Docker.
CMD ["/bin/sh", "-c", "exec streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless true --browser.gatherUsageStats=false"]
