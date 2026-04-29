#!/bin/bash
set -e

# Gunicorn worker sizing
# Formula: (2 × CPU cores) + 1
# Override by setting GUNICORN_WORKERS in the environment.
CPU_CORES=$(nproc)
DEFAULT_WORKERS=$(( CPU_CORES * 2 + 1 ))
WORKER_COUNT=${GUNICORN_WORKERS:-$DEFAULT_WORKERS}

# Safety cap to avoid excessive memory use on large machines
MAX_WORKERS=9
if [ "$WORKER_COUNT" -gt "$MAX_WORKERS" ]; then
    echo "Worker count ($WORKER_COUNT) exceeds cap. Capping at $MAX_WORKERS."
    WORKER_COUNT=$MAX_WORKERS
fi

echo "--> CPU cores: $CPU_CORES"
echo "--> Gunicorn workers: $WORKER_COUNT"

# Start Gunicorn with --preload
exec gunicorn app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKER_COUNT" \
    --timeout 120