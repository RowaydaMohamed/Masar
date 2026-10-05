#!/bin/sh
# Runs every time the backend container starts.
set -e

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

# Seed demo data ONLY when asked to AND only when the database is still empty,
# so restarting the container never tries to insert duplicates.
if [ "${SEED_ON_START:-false}" = "true" ]; then
  if python manage.py shell -c "import sys; from academics.models import Department; sys.exit(0 if Department.objects.exists() else 1)"; then
    echo "==> Database already has data - skipping seed"
  else
    echo "==> Seeding demo data"
    python manage.py seed_data
  fi
fi

echo "==> Starting server"
exec "$@"