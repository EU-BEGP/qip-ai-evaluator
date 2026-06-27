#!/bin/bash
set -e

# 1. Build images
echo "--> Building images..."
docker compose build

# 2. Start all services (recreates only changed containers; no full teardown)
echo "--> Starting services..."
docker compose up
