FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

WORKDIR /app

# Install CPU-only torch from the dedicated index FIRST. The default torch wheel
# pulls ~2GB of CUDA libraries we don't need (inference runs on CPU); the CPU build
# keeps the image far smaller. The subsequent requirements install then sees torch
# already satisfied.
COPY requirements.txt .
RUN pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

# Pre-download the embedding + reranker models and the tokenizer at BUILD time, so
# containers start instantly and run fully offline/reproducibly afterwards (no
# first-request download, no dependency on HuggingFace being up at runtime).
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5', revision='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'); \
CrossEncoder('BAAI/bge-reranker-base', revision='2cfc18c9415c912f9d8155881c133215df768a70')" \
 && python -c "from transformers import AutoTokenizer; \
AutoTokenizer.from_pretrained('BAAI/bge-small-en-v1.5', revision='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a')"

COPY . .

EXPOSE 8000

# Default command runs the API; the worker overrides this in docker-compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
