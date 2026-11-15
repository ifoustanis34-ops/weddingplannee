FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        # WeasyPrint (PDF quotes, contracts, receipts, invitations)
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 wedivo
WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=10 pip install -r requirements.txt

FROM base AS dev
COPY requirements-dev.txt .
# The pip cache mount keeps downloaded wheels across builds, even failed ones (slow networks).
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=10 pip install -r requirements-dev.txt
USER wedivo
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
COPY --chown=wedivo:wedivo . .
RUN DJANGO_SECRET_KEY=build DATABASE_URL=sqlite:///tmp/build.db \
    python manage.py collectstatic --noinput --settings=config.settings.prod
# Uploaded files (photos, logos, PDF): owned by the app user, so a volume mounted here starts
# writable (Docker copies this ownership into a new named volume).
RUN mkdir -p /app/media && chown wedivo:wedivo /app/media
USER wedivo
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
