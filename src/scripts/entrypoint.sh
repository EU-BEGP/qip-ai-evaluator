#!/bin/bash
set -e

# 1. WORKER CALCULATION
if [ -z "$API_KEYS" ]; then
    if [ -n "$API_KEY" ]; then
        echo "Single API_KEY found. Using 1 worker."
        WORKER_COUNT=1
    else
        echo "No keys found! Defaulting to 1 worker."
        WORKER_COUNT=1
    fi
else
    KEY_COUNT=$(echo "$API_KEYS" | tr -cd ',' | wc -c)
    WORKER_COUNT=$((KEY_COUNT + 1))
    echo "Detected $WORKER_COUNT API Keys."
fi

# Safety Limit
MAX_WORKERS=8
if [ "$WORKER_COUNT" -gt "$MAX_WORKERS" ]; then
    echo "Worker count ($WORKER_COUNT) exceeds limit. Capping at $MAX_WORKERS."
    WORKER_COUNT=$MAX_WORKERS
fi

echo "--> Workers set to: $WORKER_COUNT"

# 2. START GUNICORN 
exec gunicorn app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKER_COUNT" \
    --timeout 120 \
    --preload
