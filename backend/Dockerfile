FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app ./app
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /app /data

FROM base AS dev
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

