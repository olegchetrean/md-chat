FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY gunicorn.conf.py ./gunicorn.conf.py
COPY scripts ./scripts

RUN pip install --upgrade pip && pip install -e . \
    && chmod +x ./scripts/gunicorn-run.sh

EXPOSE 5002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:5002/api/health || exit 1

# Production: gunicorn with gthread workers. See gunicorn.conf.py for tuning
# and docs/production-deploy.md for the deploy runbook. Use exec form so PID 1
# is gunicorn and SIGTERM from Docker reaches it directly for graceful shutdown.
CMD ["gunicorn", "-c", "gunicorn.conf.py", "md_chat_ai.api:create_app()"]
