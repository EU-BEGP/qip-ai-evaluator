#!/bin/bash

# Stop script on first error
set -e

echo "============================================"
echo "🚀 Starting Deployment: Evaluator API (Local)"
echo "============================================"

# 1. Clean up old containers
echo "--> 1. Stopping old containers..."
docker-compose down

# 2. Build new images
echo "--> 2. Building images..."
docker-compose build

# 3. Start DB first and WAIT
# Esto es crucial: Iniciamos la DB y le damos tiempo para respirar
echo "--> 3. Starting Database..."
docker-compose up -d db

echo "--> ⏳ Waiting 10 seconds for PostgreSQL to be ready..."
sleep 10

# 4. Run database migrations
# Ahora que la DB está arriba y lista, la migración funcionará
echo "--> 4. Running database migrations..."
docker-compose run --rm app python manage.py migrate

# 5. Start remaining services (attached mode)
echo "--> 5. Starting all services..."
echo "    (Press Ctrl+C to stop)"
echo "============================================"
docker-compose up