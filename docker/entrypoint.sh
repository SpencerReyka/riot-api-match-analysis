#!/bin/sh
set -eu

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn riot_api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-30}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output
