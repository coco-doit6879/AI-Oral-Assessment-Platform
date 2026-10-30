FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgomp1 bash ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Pre-download HuBERT model weights to container cache
RUN python -c "from transformers import Wav2Vec2FeatureExtractor, HubertModel; \
    m='facebook/hubert-base-ls960'; \
    Wav2Vec2FeatureExtractor.from_pretrained(m); \
    HubertModel.from_pretrained(m)"

COPY engine.py server.py ./

RUN useradd --create-home --uid 10002 gopt && chown -R gopt:gopt /app /home/gopt
USER gopt

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
