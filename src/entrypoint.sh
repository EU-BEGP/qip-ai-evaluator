#!/bin/bash
set -e

# 1. Calculate the number of keys
if [ -z "$GEMINI_API_KEYS" ]; then
    # If there is no list, check if there is a single key
    if [ -n "$GEMINI_API_KEY" ]; then
        echo "ℹ️ Single GEMINI_API_KEY found. Using 1 worker."
        WORKER_COUNT=1
    else
        echo "⚠️ No Gemini keys found! Defaulting to 1 worker."
        WORKER_COUNT=1
    fi
else
    KEY_COUNT=$(echo "$GEMINI_API_KEYS" | tr -cd ',' | wc -c)
    WORKER_COUNT=$((KEY_COUNT + 1))
    
    echo "🚀 Detected $WORKER_COUNT Gemini API Keys in rotation."
fi

# 2. Safety Limits
MAX_WORKERS=8
if [ "$WORKER_COUNT" -gt "$MAX_WORKERS" ]; then
    echo "⚠️ Worker count ($WORKER_COUNT) exceeds limit ($MAX_WORKERS). Capping at $MAX_WORKERS."
    WORKER_COUNT=$MAX_WORKERS
fi

echo "🔥 Starting Gunicorn with $WORKER_COUNT workers..."

# 3. Run Gunicorn (Replacing this script as the main process)
# --preload is essential to share memory of the loaded models
exec gunicorn app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKER_COUNT" \
    --timeout 120 \
    --preload
