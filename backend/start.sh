#!/bin/sh
# Démarrage du backend en production (Docker / Railway)
set -e

# Les apps n'ont pas de migrations : --run-syncdb crée les tables manquantes.
# Tables « auth » d'abord : sous PostgreSQL, accounts_user pointe vers auth_group.
python manage.py migrate auth --noinput
python manage.py migrate --run-syncdb --noinput

exec gunicorn sunutribunal.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile -
