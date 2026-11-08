# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ENV APP_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY apps/hymns-pipeline/requirements.lock /tmp/requirements.lock
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r /tmp/requirements.lock
# Preserve the repository layout used by the pipeline's paths and shared schemas.
COPY apps/hymns-pipeline apps/hymns-pipeline
COPY packages/hymns-contracts/schemas packages/hymns-contracts/schemas
COPY packages/firebase/src/seed packages/firebase/src/seed
RUN groupadd --gid 10001 pipeline && useradd --uid 10001 --gid pipeline --create-home pipeline \
    && chmod -R a+rX /app \
    && chown -R pipeline:pipeline /app
USER pipeline
ENTRYPOINT ["python", "apps/hymns-pipeline/run.py"]
CMD ["check"]
