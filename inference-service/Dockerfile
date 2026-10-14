# inference-service — nạp cả ai-core (cùng image) để import ai_core như thư viện.
FROM python:3.11-slim

WORKDIR /srv

# torch CPU mặc định; đổi sang cu121 wheel khi deploy GPU RTX 3060.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY inference-service/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-core/ai_core /srv/ai-core/ai_core
COPY inference-service /srv/inference-service
COPY backend/ingest-worker /srv/ingest-worker

ENV PYTHONPATH=/srv/ai-core
WORKDIR /srv/inference-service
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
