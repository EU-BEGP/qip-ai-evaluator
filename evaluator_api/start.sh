#!/bin/bash
set -e

# 1. Stop running containers
echo "--> Stopping containers..."
docker-compose down

# 2. Build images
echo "--> Building images..."
docker-compose build

# 3. Start all services
echo "--> Starting services..."
docker-compose up