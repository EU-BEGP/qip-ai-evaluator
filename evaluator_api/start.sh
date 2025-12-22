#!/bin/bash
set -e

echo "============================================"
echo "Starting Deployment: Evaluator API"
echo "============================================"

# 1. Clean up old containers
echo "--> 1. Stopping old containers..."
docker-compose down

# 2. Build new images
echo "--> 2. Building images..."
docker-compose build

# 3. Start DB first and WAIT
echo "--> 3. Starting Database..."
docker-compose up -d db

echo "--> Waiting 5 seconds for PostgreSQL..."
sleep 5

# 4. Run database migrations
echo "--> 4. Running database migrations..."
docker-compose run --rm app python manage.py migrate

# 4b. Static Files
IS_DEV=$(grep "ENVIRONMENT=development" .env || true)
if [ -z "$IS_DEV" ]; then
    echo "--> 4b. Production detected: Collecting Static Files..."
    docker-compose run --rm app python manage.py collectstatic --noinput
else
    echo "--> 4b. Development detected: Skipping collectstatic."
fi

# 5. Start remaining services
echo "--> 5. Starting all services..."
echo "    (Press Ctrl+C to stop)"
echo "============================================"
docker-compose up