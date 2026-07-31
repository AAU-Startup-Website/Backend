#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

if [ "${SEED_PHASES:-false}" = "true" ]; then
  echo "Seeding phases..."
  python manage.py seed_phases || true
fi

if [ "${COLLECTSTATIC:-false}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

echo "Starting Gunicorn..."
exec gunicorn startup_portal.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
