#!/bin/bash

# Stop script on first error
set -e

echo "============================================"
echo "🚀 Starting Deployment: Evaluator API (Local)"
echo "============================================"

# 1. Clean up old containers
#    (Use 'docker-compose down -v' if you want to WIPE the database every time)
echo "--> 1. Stopping old containers..."
docker-compose down

# 2. Build new images
echo "--> 2. Building images..."
docker-compose build

# 3. Make & Run Migrations (The missing step!)
echo "--> 3. Updating Database Schema..."
docker-compose run --rm app python manage.py migrate

# 4. Start services
echo "--> 4. Starting services..."
echo "    (Press Ctrl+C to stop)"
echo "============================================"
docker-compose up
