#!/bin/bash
set -e

# 1. Wait for DB
echo "--> Waiting for database..."
while ! pg_isready -h db -U $POSTGRES_USER; do
  echo "Database not ready..."
  sleep 2
done

echo "--> Database is ready!"

# 2. Run migrations
echo "--> Running migrations..."
python manage.py migrate

# 3. Static files
if [ "$ENVIRONMENT" != "development" ]; then
    echo "--> Collecting static files..."
    python manage.py collectstatic --noinput
fi

# 4. Ensure logs directory exists
mkdir -p /app/logs

# 5. Start app
if [ "$ENVIRONMENT" = "development" ]; then
    echo "--> Running development server..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "--> Running Gunicorn..."
    exec gunicorn \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --timeout 180 \
        evaluator_api.wsgi:application
fi