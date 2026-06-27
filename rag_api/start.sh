#!/bin/bash
set -e

echo "============================================"
echo "Starting Deployment: RAG API"
echo "============================================"

# 1. Build new images
echo "--> 1. Building images..."
docker compose build

# 2. Pre-build the vector store (runs once; skipped if already up to date)
echo "--> 2. Pre-building vector store..."
docker compose run --rm app python manage.py shell -c "
from apps.evaluator.bootstrap import build_knowledge_base_auto, load_criteria_auto
build_knowledge_base_auto()
load_criteria_auto()
print('Vector store ready.')
"

# 3. Start services (recreates only changed containers; no full teardown)
echo "--> 3. Starting services..."
echo "    (Ctrl+C to detach; tmux keeps it running)"
echo "============================================"
docker compose up
