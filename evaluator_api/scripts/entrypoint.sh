#!/bin/bash
set -e

if [ "$ENVIRONMENT" = "development" ]; then
    echo "--> Development: Running runserver..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "--> Production: Running Gunicorn..."
    exec gunicorn --bind 0.0.0.0:8000 --timeout 900 evaluator_api.wsgi:application
fi