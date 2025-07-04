#!/bin/bash
set -e

ENV=prod

export ENV
export DOCKER_BUILDKIT=1

echo "Building and pushing core-service from monorepo root..."

# Build with cache from the latest image
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 core-service

# Push the image to the registry
docker compose push core-service

echo "$ENV main_project build and push completed successfully."
