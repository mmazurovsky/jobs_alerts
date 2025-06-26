#!/bin/bash

# Deploy script for Jobs Alerts Core Service

set -e

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Build the Docker image
echo "Building Docker image..."
docker-compose build

# Stop existing container if running
echo "Stopping existing container..."
docker-compose down || true

# Start the new container
echo "Starting new container..."
docker-compose up -d

# Show logs
echo "Container started. Showing logs..."
docker-compose logs -f 