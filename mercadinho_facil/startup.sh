#!/bin/sh
# Comando de inicialização do Azure App Service (configurado como "sh startup.sh")
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py criar_admin
exec gunicorn --bind=0.0.0.0:8000 --workers 1 --threads 4 --timeout 120 \
    --access-logfile - --error-logfile - mercadinho.wsgi:application
