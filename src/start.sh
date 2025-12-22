#!/bin/bash

# Stop script on first error
set -e

echo "============================================"
echo "Starting Deployment: RAG API"
echo "============================================"

# 1. Clean up old containers
echo "--> 1. Stopping old containers..."
docker-compose down

# 2. Build new images
echo "--> 2. Building images..."
docker-compose build

# 3. Run database migrations
echo "--> 3. Running database migrations..."
docker-compose run --rm app python manage.py migrate

# 4. Start services
echo "--> 4. Starting services..."
echo "    (Press Ctrl+C to stop)"
echo "============================================"
docker-compose up