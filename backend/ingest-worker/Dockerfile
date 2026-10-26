FROM scratch AS sources
COPY backend/ingest-worker/main.py backend/ingest-worker/requirements.txt /ingest-worker/
# Reuse the existing DSP exactly; no model, inference service or checkpoint.
COPY ai-core/ai_core/audio/features.py ai-core/ai_core/audio/mel.py /ai_core/audio/

FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/srv
WORKDIR /srv
COPY --from=sources /ingest-worker/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY --from=sources / /srv/
WORKDIR /srv/ingest-worker
CMD ["python", "/srv/ingest-worker/main.py"]
