FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt \
    && python -m pip uninstall --yes pip setuptools wheel

COPY --chown=app:app . .
RUN mkdir -p /app/staticfiles \
    && chown app:app /app/staticfiles \
    && chmod 0555 /app/docker/entrypoint.sh

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request; host=os.environ.get('DJANGO_ALLOWED_HOSTS','localhost').split(',')[0]; request=urllib.request.Request('http://127.0.0.1:8000/healthz',headers={'Host':host,'X-Forwarded-Proto':'https'}); raise SystemExit(0 if urllib.request.urlopen(request,timeout=3).status == 200 else 1)"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
