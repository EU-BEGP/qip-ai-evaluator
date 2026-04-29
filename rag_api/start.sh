#!/bin/bash
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

# 3. Pre-build the vector store (runs once; skipped if already up to date)
echo "--> 3. Pre-building vector store..."
docker-compose run --rm app python manage.py shell -c "
from apps.evaluator.init_knowledge import build_knowledge_base_auto, load_criteria_auto
build_knowledge_base_auto()
load_criteria_auto()
print('Vector store ready.')
"

# 4. Start services
echo "--> 4. Starting services..."
echo "    (Press Ctrl+C to stop)"
echo "============================================"
docker-compose up
